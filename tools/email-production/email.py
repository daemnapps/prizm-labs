#!/usr/bin/env python3
"""One swiped email (or any lane's teardown record) in; one built email out.
Ten stages, all Claude, all text — then `render.py` draws it.

    python3 email.py <source> --brand brand-a \
        --product brands/brand-a/products/glow-body-scrub/product.md \
        [--subjects 5] [--label sale-01] [--brand-root <tree>]

Mirrors copy/copy.py stage for stage, deliberately: the two lanes are one
machine and a fix in either is worth porting to the other. Read
STAGE-DELTAS.md for what email changes and what it leaves alone.

Runs under the operator's own `claude` login. No API key, no board watcher —
this is a standalone run today; if it becomes a daily habit the way video
teardown did, it earns that infrastructure then, not before.
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
from pathlib import Path

from paths import HERE, WORKSPACE, calendar_tool, lab_tool, component
sys.path.append(str(component("brandpath")))   # appended, never ahead of this machine
import brandpath as BP                                # noqa: E402

# The brand index and the language query already exist in the copy lane and
# are lane-agnostic. Importing beats a second copy that drifts: one fix, both
# lanes. If the copy lane is absent the chain still runs — the scout gets an
# empty index and says so, which is honest, rather than the run dying.
sys.path.insert(0, str(component("copywriter", "machine")))
try:
    import context
    import language as L
except Exception as e:                                    # pragma: no cover
    context = L = None
    print(f"note: copy context/language not importable ({e}) — "
          "the scout and the language layer run empty")

PROMPTS = HERE / "prompts"
DEFAULT_MODEL = "claude-opus-5"

# A MODEL PER JOB, NOT OPUS EVERYWHERE (the owner, 2026-09-15: "can we use another
# model to do some of the writing… so we can run work simultaneously").
#
# Ten stages ran Opus because one `--model` covered the whole chain, and a
# month of sends is ten Opus calls apiece. But the stages are not one kind of
# work. Four of them READ — they pull an existing email apart, or sift files
# the brand already wrote, and the answer is in the input. Three JUDGE against
# rules that are written down. Three DESIGN: they decide what this email
# argues, what it is called, and what its words are, and a weaker model there
# is visible in the copy.
#
# So: `reads` extracts, `checks` applies stated rules, `designs` makes the
# calls nobody wrote down. Naming the tier per stage (rather than the model)
# keeps this readable when the model names change again.
TIERS = {
    "reads":   "claude-haiku-4-5-20251001",
    "checks":  "claude-sonnet-5",
    "designs": "claude-opus-5",
}

# Roughly what a 200k-token window holds in characters, kept deliberately
# conservative: the cost of escalating a stage that would have fit is one
# stage on a dearer model, and the cost of NOT escalating one that does not
# fit is the whole email dying four minutes in.
SMALL_WINDOW_CHARS = 350_000

# The chain's shape, in one place. render.py and any future board read this,
# so the page and the runner can never disagree about what a stage is called.
STAGES = [
    dict(key="stage0", tier="reads", id="0", name="Triage", group="READ THE SOURCE",
         label="triage",
         blurb="Which lane, which email format, whose voice, whose name it sends under."),
    dict(key="stage1", tier="checks", id="1", name="Read", group="READ THE SOURCE",
         label="record",
         blurb="One email in, one objective record out — envelope, blocks, CTAs, weight, voice."),
    dict(key="stage2", tier="designs", id="2", name="Spec", group="READ THE SOURCE",
         label="spec",
         blurb="The record abstracted into a brand-free, medium-free construct."),
    dict(key="stage1b", tier="reads", id="2b", name="Context scout", group="READ THE SOURCE",
         label="context",
         blurb="Sifts everything the brand knows, picks what THIS source needs, says what it left out."),
    dict(key="stage1c", tier="reads", id="2c", name="Live read", group="READ THE SOURCE",
         label="live",
         blurb="The week this email lands in, in checkable facts — and how it invites "
               "the reader to engage with the moment on top of the offer."),
    dict(key="stage3", tier="designs", id="3", name="Injection", group="MAKE IT OURS",
         label="injection",
         blurb="Substitution, never rewrite — the construct is the template."),
    dict(key="stage4", tier="checks", id="4", name="Placement", group="MAKE IT OURS",
         label="placement",
         blurb="Where the product enters, the scroll budget, the CTA plan, the image plan."),
    dict(key="stage5", tier="designs", id="5", name="Subject lines", group="MAKE IT OURS",
         label="subjects",
         blurb="Control plus variations, each a subject AND its preview. All ship — the machine never picks."),
    dict(key="stage6", tier="checks", id="6", name="Expansion", group="MAKE IT OURS",
         label="expansion",
         blurb="Gated moves that build commercial structure. Skipped when the source is already an ad.",
         gated_on_lane="ORGANIC"),
    dict(key="stage7", tier="designs", id="7", name="Close", group="MAKE IT OURS",
         label="close",
         blurb="The objection at the flinch, the landing, and the PS — or an honest NO PS."),
    dict(key="stage8", tier="designs", id="8", name="Build", group="WHAT SHIPS",
         label="blocks",
         blurb="The email in the simple shape: headline, hero picture, copy, optional offer, one button (2026-09-19)."),
    dict(key="stage8c", tier="checks", id="8c", name="Check", group="WHAT SHIPS",
         label="check",
         blurb="Product facts against the files, the email read aloud for chopped thoughts, typos. Anything found holds it from Klaviyo."),
    dict(key="stage9", tier="reads", id="9", name="Brief", group="WHAT SHIPS",
         label="brief",
         blurb="The one document the person building it in Klaviyo opens."),
]
SPEC = {s["key"]: s for s in STAGES}

LANE_LINE = re.compile(r"^\**LANE:?\**\s*:?\s*`?([A-Z][A-Z ]+)", re.M)
FORMAT_LINE = re.compile(r"^\**FORMAT:?\**\s*:?\s*`?([a-z0-9-]+)", re.M)
SENDER_LINE = re.compile(r"^\**SENDER:?\**\s*:?\s*`?([A-Z-]+)", re.M)
AVATAR_LINE = re.compile(r"^\**AVATAR:?\**\s*:?\s*`?([a-z0-9-]+)", re.M)
FUNNEL_LINE = re.compile(r"^\**FUNNEL:?\**\s*:?\s*`?(prospect|lead|customer|churned)", re.M)


def _first(pattern, text):
    m = pattern.search(text or "")
    return m.group(1).strip() if m else None


def sha(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else None


def read(path, required=False):
    if not path:
        return ""
    p = Path(os.path.expanduser(str(path)))
    if not p.is_file():
        p = WORKSPACE / path
    if not p.is_file():
        if required:
            sys.exit(f"missing required file: {path}")
        return ""
    return p.read_text().strip()


def doctrine(slice_name):
    """A Schwartz doctrine slice, bound by path — never restated in a prompt.
    Rendered by components/marketing-doctrine/render.py from frameworks.json."""
    return read(f"components/marketing-doctrine/slices/{slice_name}.md")


def latest_prompt(stage):
    """Highest -vN- wins, same rule as every other lane."""
    best, best_v = None, -1
    for f in PROMPTS.glob(f"{stage}-*.md"):
        m = re.search(r"-v(\d+)-", f.name)
        if m and int(m.group(1)) > best_v:
            best, best_v = f, int(m.group(1))
    if not best:
        sys.exit(f"no prompt file found for {stage} in {PROMPTS}")
    return best


def claude(prompt_text, model, label=None):
    # A headless -p session still inherits this repo's project Stop hooks even
    # for a stateless prompt-in/text-out call. A blocking hook cannot prompt a
    # human, so the session writes its answer to the HOOK instead of the
    # deliverable and the output is silently wrong (hit in copy,
    # 2026-08-24). Keep this repo's tree clean of whatever a Stop hook guards
    # before running the chain.
    r = subprocess.run(
        ["claude", "-p", "--model", model, "--output-format", "text"],
        input=prompt_text + "\n\nReturn only the deliverable. No tools, no preamble.",
        capture_output=True, text=True,
    )
    if r.returncode and "limit" in (r.stdout or "").lower():
        # Out of usage is not a broken stage. Say it in one line so a month run
        # reads as "stopped: account limit" rather than twelve mystery failures.
        sys.exit(f"USAGE LIMIT — stage {label or '?'} on {model} was refused: "
                 f"{r.stdout.strip()[:240]}")
    if r.returncode:
        # A dead stage used to report `a stage failed:` and nothing else —
        # `claude` exits non-zero with an empty stderr when the prompt will not
        # fit, so the one message that mattered was the one never printed.
        # Say which stage, which model, and how big the prompt was: those three
        # facts name this failure outright (2026-09-15).
        # built apart: a string split across lines INSIDE an f-string's braces
        # parses only on Python 3.12+, and the mini runs 3.9
        err = (r.stderr[:400].strip()
               or "(empty — usually the prompt exceeding the model window)")
        sys.exit(f"stage {label or '?'} failed on {model} "
                 f"(prompt {len(prompt_text)/1e6:.2f}MB, exit {r.returncode})\n"
                 f"  stderr: {err}\n"
                 f"  stdout: {r.stdout[:200].strip() or '(empty)'}")
    return r.stdout.strip()


def catalogue_path(brand):
    """The type catalogue is the BRAND's knowledge (moved 2026-08-31, the owner's
    brand-agnostic ruling). A brand without one starts from the tool's clean
    seed — and should copy it into its folder to own it."""
    p = WORKSPACE / "brands" / brand / "email-sms" / "email-types.json"
    if p.is_file():
        return p
    print(f"     NOTE: {brand} has no email/email-types.json — running on the "
          "generic seed catalogue. Copy the seed into the brand folder to own it.")
    return calendar_tool("definitions/send-types.seed.json")


def render_types(path):
    """The type catalogue as triage reads it.

    There used to be a second file, formats.md, listing what a SOURCE could
    be — a separate vocabulary for the same question the type catalogue
    already answers. Two lists of email kinds is how a source gets triaged as
    one thing and written as another. One list now, rendered.
    """
    d = json.loads(Path(path).read_text())
    cat = {"ask": "Promotional — made of our offer",
           "help": "Educational — made of our expertise",
           "belong": "Cultural — made of the world outside",
           "real": "Community — made of our customers",
           "brand": "Brand — made of us",
           "affiliate": "Affiliate — made of a partner's offer"}
    out = ["The kinds of email this brand knows. Answer with ONE key.", "",
           "A shape genuinely not here is reported as `unlisted` with a one-line",
           "description — never forced into the nearest key, because a forced key",
           "mis-binds every stage after it.", ""]
    for k, label in cat.items():
        out.append(f"## {label}")
        out.append("")
        for x in d["types"]:
            if x["well"] == k:
                out.append(f"- `{x['key']}` — {x['name']}: {x['what']}")
        out.append("")
    out += ["## Treatments — not kinds, but how a kind is played", ""]
    out += [f"- `{x['key']}` — {x['name']}: {x['what']}" for x in d.get("treatments", [])]
    return "\n".join(out)


def message_only(record):
    """The record as the WRITING steps get it: the message and the source's
    defects, with the PAGE FURNITURE section taken out (2026-09-20).

    Seen live: the writer copied a source email's nav and footer words into the
    new email's body. The read step (v2) now files those under their own
    `# PAGE FURNITURE` heading; the spec step reads the whole record so it can
    refuse them by name, and every step after it never sees them at all. A
    record with no such heading (an older run, another lane's teardown) passes
    through untouched."""
    m = re.search(r"^#{1,3}\s*\**PAGE FURNITURE\**\s*$", record or "", re.M)
    if not m:
        return record
    rest = record[m.end():]
    nxt = re.search(r"^#{1,3}\s*\**SOURCE DEFECTS\**\s*$", rest, re.M)
    note = ("(The source's page furniture — logo row, navigation, category links, social "
            "row, footer, legal — was recorded separately and is deliberately not shown "
            "here. It is not part of the message.)\n\n")
    return record[:m.start()] + note + (rest[nxt.start():] if nxt else "")


def fill(template, fields):
    """Deterministic substitution, so a run can be replayed without a model."""
    out = template
    for name, value in fields.items():
        out = out.replace("{" + name + "}", str(value) if value else "(none supplied)")
    return out


# REUSE WHAT IS ALREADY WRITTEN (2026-09-19). `--rerun-from stage8` keeps every
# stage before stage 8 exactly as it is on disk and runs only from there on.
# The simple-email decision changed ONE stage — the layout — and re-buying
# nine stages of reading and writing to change the tenth is how a month of
# emails costs twice.
RERUN_FROM = None


def creative_qc(tool, stage, run_dir, output, given=None, items=None):
    """THE CREATIVE QC LOOP (the owner, 2026-10-02: "installed for each of my
    production tools … for all stages in the creation process"): the output is
    reviewed against what it was given and the stage's bars
    (components/quality-checks/definitions/stages.json); the round is filed in
    <run>/qc-log/. Never stops the run on its own."""
    try:
        here = Path(__file__).resolve()
        comp = next(p for p in here.parents if (p / "components" / "quality-checks" / "marketing_chain_checks").is_dir())
        q = str(comp / "components" / "quality-checks")
        if q not in sys.path:
            sys.path.insert(0, q)
        from marketing_chain_checks import review
        f = review.after_stage(tool, stage, run_dir, output=output, items=items,
                               sources=[given] if given and Path(given).exists() else None)
        bad = [k for k, v in f.items() if isinstance(v, dict) and v.get("severity") in ("BLOCKER", "FIX")]
        if bad:
            print(f"  QC {stage}: {len(bad)} finding(s) — see qc-log/QC-LOG.md")
        return f
    except Exception as e:
        print(f"  QC {stage}: review not run ({type(e).__name__})")
        return {}


def run_stage(stage, out_dir, model, state, **fields):
    spec = SPEC[stage]
    order = [s["key"] for s in STAGES]
    saved = out_dir / f"{stage}--{spec['label']}.md"
    if (RERUN_FROM and order.index(stage) < order.index(RERUN_FROM)
            and saved.is_file()):
        print(f"  == {stage}  (kept from the earlier run)")
        state["stages"][stage] = {"status": "reused", "out": saved.name}
        return saved.read_text().strip()
    prompt_file = latest_prompt(stage)
    filled = fill(prompt_file.read_text(), fields)
    # The prompt AS ACTUALLY SENT, beside its output. Without it all anyone can
    # read back is the template, and the template is not what ran.
    sent_path = out_dir / f"{stage}--sent.md"
    sent_path.write_text(filled)

    # SIZE ESCALATES THE MODEL, and the tier only proposes (2026-09-15).
    # A stage's tier says what KIND of thinking it does. It cannot say how much
    # the stage is handed, and that is a per-brand fact: the context scout gets
    # everything a brand knows, which is 134KB for a young brand and 1.7MB for
    # an old one. Tiering the scout as a `reads` job was right about the job
    # and fatal in practice — every brand-b email died there while every brand-a
    # email passed, because one prompt fit a small window and the other did
    # not. Deciding on the measured prompt means a brand can grow past a model
    # without anyone remembering to re-tier it.
    if len(filled) > SMALL_WINDOW_CHARS and model != TIERS["designs"]:
        print(f"     {stage}: prompt is {len(filled)/1e6:.2f}MB — past a small "
              f"window; escalated {model} -> {TIERS['designs']}")
        model = TIERS["designs"]

    print(f"  -> {stage}  ({prompt_file.name})")
    t0 = time.time()
    output = claude(filled, model, stage)
    seconds = round(time.time() - t0, 1)

    out_path = out_dir / f"{stage}--{spec['label']}.md"
    out_path.write_text(output + "\n")
    creative_qc("email-production", stage, out_dir, out_path, sent_path)
    state["stages"][stage] = {
        "status": "done", "seconds": seconds, "chars_out": len(output),
        "model": model,
        "prompt_file": str(prompt_file.relative_to(HERE)),
        "prompt_name": prompt_file.name,
        "prompt_sha256_12": sha(prompt_file),
        "wants": sorted(fields.keys()),
        "out": out_path.name, "sent": sent_path.name,
    }
    return output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="a swiped email (text or .eml), or a teardown "
                                   "record from any other lane")
    ap.add_argument("--brand", required=True, help="brand folder name under brands/")
    ap.add_argument("--avatar", default=None,
                    help="which core avatar this run is for. Every language "
                         "bank, profile and sub-avatar resolves through it. "
                         "OMIT IT for an email that genuinely addresses "
                         "everyone — a sitewide sale, a milestone, a mission "
                         "note. Omitting is a declaration, not a default: the "
                         "stages are told there is no avatar and must not write "
                         "as though there were one.")
    ap.add_argument("--product", default=None,
                    help="which product this is about — a key from "
                         "brands/<brand>/products/ (e.g. widget, gadget, "
                         "daily-set), or a path. What the thing IS.")
    ap.add_argument("--offer", default=None,
                    help="which offer this email carries — a key from the "
                         "offer bank (e.g. widget-preorder). The commercial "
                         "construction around the product: price, bundle, "
                         "terms. A product and an offer are different things, "
                         "and one product carries many offers. Omit for an "
                         "email that carries no offer at all.")
    ap.add_argument("--source-reference", default=None,
                    help="where the source came from, for the brief")
    ap.add_argument("--type", default=None, dest="email_type",
                    help="the calendar send's type — an email format. Checked "
                         "against the element library (components/elements, "
                         "format/email) and the brand's own email-types.json "
                         "before any step runs; unknown in both is refused.")
    ap.add_argument("--angle", default=None,
                    help="the specific argument this send should make, if the "
                         "plan that scheduled it already chose one (a variant's "
                         "angle from a calendar slot). Omit for a run with no "
                         "prior angle decided — injection reasons from the "
                         "avatar and language bank alone.")
    ap.add_argument("--note", default=None,
                    help="the REVIEWER's instruction for this one send, written "
                         "on the calendar board before the copy was triggered "
                         "(2026-09-13). It outranks the angle and the source: a "
                         "person read this slot, said what to fix, and pressed "
                         "the button. Omit when nobody left a note.")
    ap.add_argument("--occasion", default=None,
                    help="the moment this send was scheduled FOR — a holiday, a "
                         "season, a cultural event. RULED 2026-09-10 (the owner: "
                         "'this literally has nothing to do with football'): the "
                         "calendar picked the slot because of this, so the "
                         "writing stages are told it. It used to reach stage 0 "
                         "and the brief header only, as a filing label, and every "
                         "stage that writes a word never saw it.")
    ap.add_argument("--affiliate", default=None,
                    help="the roster key of the PARTNER this send features, from "
                         "brands/<brand>/email-sms/affiliates.json (2026-09-21). It binds "
                         "no prompt — the partner's facts and terms already ride in "
                         "--note. It is recorded so the delivery gate can check the "
                         "finished email against that partner's own record: their real "
                         "link, and no earnings claim on a traffic-only arrangement.")
    ap.add_argument("--send-date", default=None,
                    help="the date this email actually goes out, ISO. The copy "
                         "borrowed the swiped email's weekday otherwise, so "
                         "September sends said 'It's Monday' on a Saturday.")
    ap.add_argument("--segment", default=None,
                    help="which of the brand's eight segments this send targets "
                         "— a calendar slot's `segment` field, carried through so "
                         "triage can name the awareness level it is actually "
                         "writing to. Omit for a send with no calendar slot; "
                         "triage then defaults to a list email's usual reader.")
    ap.add_argument("--research", default=None,
                    help="a file of live research about the week this send lands "
                         "in — what is actually happening, with sources. Written "
                         "by whoever ran the research (live_read.py prints the "
                         "brief that says what to go and find). RULED 2026-09-10: "
                         "every email gets one, not just the ones on a moment. "
                         "Without it stage 1c still runs and says the week is "
                         "unresearched, which is honest and useless — so supply it.")
    ap.add_argument("--subjects", default="5",
                    help="how many subject/preview variations beyond the control")
    ap.add_argument("--label", default=None, help="run label; defaults to the source filename stem")
    ap.add_argument("--model", default=None,
                    help="Force ONE model for every stage, overriding the "
                         "per-stage tiers. Omit for the normal run, where each "
                         "stage uses the tier its job earns.")
    ap.add_argument("--rerun-from", default=None, metavar="STAGE",
                    help="keep every earlier stage's saved output and run from "
                         "this stage on, e.g. --rerun-from stage8")
    ap.add_argument("--tier", action="append", default=[], metavar="NAME=MODEL",
                    help="Override one tier, e.g. --tier reads=claude-sonnet-5. "
                         "Repeatable.")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve every variable and report what was found, "
                         "then stop. No model calls, no cost — this is how a "
                         "wiring change gets checked.")
    ap.add_argument("--brand-root", default=None,
                    help="tree holding brands/<brand>/ — defaults to the shared workspace")
    args = ap.parse_args()

    # One knob, honoured everywhere brand files are read, so the scout and the
    # runner can never end up indexing two different trees.
    global WORKSPACE
    if args.brand_root:
        root = Path(os.path.expanduser(args.brand_root)).resolve()
        if not (root / "brands").is_dir():
            sys.exit(f"--brand-root has no brands/ inside it: {root}")
        WORKSPACE = root
        if context:
            context.WORKSPACE = root
    # The brand tree is found by SHAPE, never assumed (ported from copy.py
    # 2026-09-01, after email.py went blind the same way copy.py did on
    # 2026-08-30): --brand-root wins when given; otherwise probe the trees a
    # brand actually lives in and take the first that holds this brand's
    # banks. avatar_root() returns a default (not None) even when the brand
    # isn't there, so an unprobed root doesn't raise — it just silently hands
    # back an empty roster.
    if args.brand_root:
        BRAND_TREE = root
    else:
        BRAND_TREE = None
        for cand in (WORKSPACE / "lab", WORKSPACE):
            if L and L.avatar_root(args.brand, cand).is_dir():
                BRAND_TREE = cand
                WORKSPACE = cand
                if context:
                    context.WORKSPACE = cand
                break
        if BRAND_TREE is None:
            BRAND_TREE = WORKSPACE
    print(f"brand context: {WORKSPACE}")

    # THE ELEMENTS GATE — before anything is spent. The send's type is an email
    # format; a type nobody has defined would be written as whatever triage
    # guessed. Asked of components/elements (format/email) and the brand's own
    # email/email-types.json.
    elements_picked = {}
    if args.email_type:
        sys.path.insert(0, str(HERE / "machine"))
        import email_elements as EE
        why = EE.type_problem(args.brand, args.email_type, WORKSPACE)
        if why:
            sys.exit(f"HELD at the elements gate — {why}")
        elements_picked = EE.picked(args.brand, args.email_type, workspace=WORKSPACE)

    label = args.label or Path(args.source).stem
    # Output lives under runs/, keyed by the machine's spoken name, never
    # beside the code (lab/CLAUDE.md, ruled 2026-09-17). results/ is
    # history: a run begun there before the move is picked up from there once,
    # so --rerun-from can reuse its stages, and continues in its new home.
    out_dir = WORKSPACE / "runs" / "email-production" / args.brand / label
    old = HERE / "results" / label
    # A DRY RUN WRITES NOTHING (2026-09-20). It used to make the run folder —
    # and carry an old run into it — before it knew it was only looking, so the
    # doctor had to delete a folder under runs/ after every check.
    if not args.dry_run:
        if not out_dir.exists() and old.is_dir() and args.rerun_from:
            import shutil
            shutil.copytree(old, out_dir)
            print(f"     carried the earlier stages over from results/{label}")
        out_dir.mkdir(parents=True, exist_ok=True)

    # Where a brand keeps its files is the BRAND's business. A map in this
    # build wins, because the brand tree is read-only and pointing at it is
    # our business; a brand that ships its own map is honoured too.
    brand_root = WORKSPACE / "brands" / args.brand
    # The lab layout, resolved through the avatar this run declared. The
    # previous version encoded a different brand's folder shape (customer/,
    # commerce/, creative/) and every variable resolved to nothing — silently,
    # because a missing optional file is not an error.
    # No avatar is a legitimate run. An email addressing everyone has no
    # avatar-shaped context to read, and reaching for the biggest bank
    # "because it is mostly them" is exactly the silent assumption this
    # refuses to make.
    A = f"core-avatars/{args.avatar}" if args.avatar else None
    conventional = {
        "avatar": f"{A}/profile.md" if A else None,
        "language_bank": f"{A}/language/rules.md" if A else None,
        "objection_bank": "core-avatars/objection-bank.md",
        "offer_file": "products/offer-bank.md",
        "proven_angles": "existing-content/angles.md",
        # Who the brand may actually name. Built 2026-09-10 after a football
        # send reached for a hockey player because he was the only athlete
        # anywhere in the files.
        "notable_customers": "core-avatars/notable-customers.json",
        # Whose week the live read is describing. Without it the stage refuses
        # to assume a country, which is correct and useless.
        "market": "market.md",
        # Neither exists yet for any brand here. Named so the NOTE prints and
        # the hole is visible rather than assumed filled.
        "hook_ledger": f"{A}/hook-ledger.md" if A else None,
        # Lives in the build, not the brand tree: it is a ruling about how we
        # send, not a fact about the customer.
        "sender_identity": None,
    }
    declared = {}
    # One map per brand PER SURFACE. Email marketing needs different variables
    # from video ad scripts, ad copy or static ads — they are different jobs
    # against the same brand, and a single shared map would have to be the
    # union of all of them (the owner, 2026-08-27).
    # The map is the BRAND's, one file per surface. This tool reads
    # variables/email.md; the static-ad tool will read variables/static-ads.md
    # off the same brand. A tool that keeps its own copy of a brand's map is a
    # tool that will disagree with the next one.
    # variables/email.md is this surface's map; chain-variables.md is the
    # legacy fallback name.
    for f in (BP.brand_path(brand_root.name, "variables", "email.md", root=brand_root.parent),
              brand_root / "chain-variables.md"):
        if f.is_file():
            # `{avatar}` and `avatar` both parse. The braced form is what the
            # brand's own chain-variables.md uses, and the bare-key-only
            # version of this regex silently matched nothing at all — no
            # error, no "brand map:" line, six empty variables.
            for m in re.finditer(r"^\s*\|?\s*`\{?([a-z_]+)\}?`\s*\|\s*`([^`]+\.(?:md|json))`",
                                 f.read_text(), re.M):
                declared[m.group(1)] = m.group(2)
            if declared:
                print(f"     brand map: {f.name} ({len(declared)} vars)")
                break

    def brand_file(var):
        rel = declared.get(var, conventional.get(var))
        if not rel:
            return ""
        # A map writes `core-avatars/<avatar>/profile.md` because it is
        # read by people as well as by this. Taking that literally is how the
        # avatar and language bank silently went missing the moment the map
        # started parsing at all.
        if "<avatar>" in rel:
            if not args.avatar:
                return ""
            rel = rel.replace("<avatar>", args.avatar)
        p = Path(rel)
        return read(p if p.is_absolute() or (WORKSPACE / p).is_file()
                    else BP.resolve_rel(brand_root.name, rel, root=brand_root.parent))

    # The avatar is validated against the brand's real roster before anything
    # is read, so a typo fails here rather than silently resolving every path
    # to a folder that does not exist.
    roster_keys = {a["key"] for a in (L.avatars(args.brand, BRAND_TREE) if L else [])}
    if args.avatar and roster_keys and args.avatar not in roster_keys:
        sys.exit(f"--avatar {args.avatar!r} is not one of this brand's avatars: "
                 + ", ".join(sorted(roster_keys)))

    if not args.avatar:
        print("     NOTE: no --avatar — this email addresses everyone. No "
              "avatar profile, no language bank, no sub-avatars; the stages "
              "are told so and must not write as though targeted.")
    avatar = brand_file("avatar")
    language_bank = brand_file("language_bank")
    offer_file = brand_file("offer_file")
    objection_bank = brand_file("objection_bank")
    hook_ledger = brand_file("hook_ledger")
    sender_identity = brand_file("sender_identity")
    proven_angles = brand_file("proven_angles")
    notable_customers = brand_file("notable_customers")
    # An OFFER narrows the bank to one construction — plus the guarantee and
    # the standing rules, which bind whatever else is on the table. Without
    # --offer the whole bank is passed and stage 4 decides what the email may
    # carry, which is the right default for anything that is not selling.
    # THE OFFER MUST BE ONE THE BRAND MAY ACTUALLY RUN, on this date, for this
    # lane (RULED 2026-09-10, the owner: "so there's an offer bank issue then…").
    # A draft with no price, an expired one, or a dated one whose moment has
    # passed all used to be assignable — a Labor Day price sat under `## Live`
    # with no end date and kept getting picked for late-September sends.
    if args.offer and args.offer != "none":
        import offers as OFFERS
        why = OFFERS.refuse(args.brand, args.offer, args.avatar, args.send_date)
        if why:
            ok = OFFERS.usable(args.brand, args.avatar, args.send_date)
            sys.exit(f"this send may not carry that offer — {why}\n"
                     f"  usable here: "
                     + (", ".join(r["key"] for r in ok) or "NOTHING. The bank has no live "
                        "offer for this lane on this date; the send has to earn instead."))

    # WHAT THIS SEND MAY SELL, decided by the calendar and binding on the copy
    # (RULED 2026-09-10, the owner: "I still see some labor day email in the figma
    # for late september… why are you not using the calendar in this chain?").
    # The calendar assigns an offer per slot, or assigns none. "None" used to
    # mean the WHOLE offer bank was handed over and the writer chose — so an
    # earns-slot with no offer shipped a Labor Day price lifted from the email
    # it was swiped from, three weeks after Labor Day.
    if args.offer and args.offer != "none":
        offer_rule = (
            f"**This send carries exactly one offer: `{args.offer}`, as written in the "
            f"bank above.** It may not name any other price, discount, bundle, gift or "
            f"deadline. An offer in the source email belongs to the source's week, not "
            f"to ours — it does not travel, and neither does the holiday attached to it.")
    else:
        offer_rule = (
            "**This send carries NO offer. The calendar decided that.** It may not name "
            "a price, a discount, a percentage, a bundle deal, a free gift, a deadline or "
            "a countdown. If the source email was built around an offer, that offer belongs "
            "to the source's week — strip it and let the argument stand on its own. Writing "
            "a price in anyway is the single worst thing this stage can do, because it puts "
            "one in front of a reader the plan deliberately did not price to.\n\n"
            "**It still ends on a product.** RULED BY DAMON 2026-09-21: \"Every email should "
            "have some sort of refocus back into a product in some capacity… even if it's more "
            "like a value email, just make sure we have the ability to make money in each of "
            "these emails.\" No offer means no PRICE, never no destination. The button goes to "
            "a real product page from the catalogue below — the one the email is about, or one "
            "of the three that carry the weight when it is about nothing in particular. A "
            "button with no destination, or one pointing at a collection or the front page "
            "instead of a product, is a failed email.")

    # WHAT MAY BE LINKED, AND WHAT IS A DRAFT (the owner, 2026-09-21: "make sure the
    # product is not a draft. FADE is a draft, so we shouldn't be talking about
    # FADE."). The brand's own files describe products that were never launched;
    # the live catalogue rides with the offer rule so every stage that already
    # reads one is handed it, and no prompt had to change to receive it.
    sys.path.append(str(HERE / "machine"))
    import brand_facts as BF
    offer_rule += "\n\n" + BF.catalogue_block(args.brand, WORKSPACE)

    # THE BANK HAS ONE SHAPE, AND ONE READER KNOWS IT (repaired 2026-09-15).
    # `offers.parse` carries the rule ruled on 2026-09-13 — an offer is a
    # `## key — Name` block, and everything below the "Ruled by a human"
    # divider is prose the writer needs but never an offer. This block was
    # written before that and still split on `###`, so the only keys it could
    # see in brand-b' bank were two GUARANTEE sub-headings: every calendar
    # assignment died as "no offer in the bank" while sitting in the file.
    # Two readers of one file disagreeing is the bug that ate the whole bank
    # once already; the fix is the same one — narrow with the reader that owns
    # the shape, never with a second rule that drifts from it.
    if args.offer and args.offer != "none" and offer_file:
        import offers as OFFERS
        MARK = "# Ruled by a human"
        catalogue, ruled = (offer_file.split(MARK, 1) + [""])[:2]
        blocks = re.split(r"^## ", catalogue, flags=re.M)
        want = [b for b in blocks if re.match(rf"{re.escape(args.offer)}\b", b)]
        if not want:
            keys = [r["key"] for r in OFFERS.parse(args.brand)]
            sys.exit(f"no offer {args.offer!r} in the bank. Known: "
                     + (", ".join(sorted(set(keys))) or "NOTHING — the bank "
                        "has no offers at all"))
        # The human-ruled half travels WHOLE. Guarantees, never-pair rules and
        # standing rules bind every send; picking among them by name is how a
        # never-pair rule goes missing from the one email that needed it.
        offer_file = "## " + "\n## ".join(want) + (f"\n\n{MARK}{ruled}" if ruled else "")
        print(f"     offer: {args.offer} (narrowed from the full bank; "
              "the human-ruled rules travel whole)")

    si = brand_root / "email-sms" / "identity" / "sender.md"
    if si.is_file():
        sender_identity = si.read_text().strip()
    # The brand's own curated ledger wins. Where it does not exist yet, the
    # ledger derived from what was actually sent stands in — stage 5 refuses to
    # reuse spent ground, and it cannot enforce that against an empty file.
    if not hook_ledger:
        derived = brand_root / "email-sms" / "ledger.md"
        if derived.is_file():
            hook_ledger = derived.read_text().strip()
            print("     hook ledger: the brand's own record of what it has sent "
                  f"({derived.parent.name}/{derived.name})")
    loaded = {"avatar": bool(avatar), "language_bank": bool(language_bank),
              "offer_file": bool(offer_file), "objection_bank": bool(objection_bank)}
    # a bare key resolves inside the brand's products/; a path is taken as given
    # A product is either `products/<key>.md` or a folder `products/<key>/`
    # with its `product.md` beside its images — brand-b keeps the first shape,
    # brand-a the second, and three brand-a emails died on "no product" while
    # the product sat in its folder (2026-09-16).
    if args.product and not Path(args.product).suffix:
        product_file = (read(BP.brand_path(brand_root.name, "products", f"{args.product}.md", root=brand_root.parent))
                        or read(BP.brand_path(brand_root.name, "products", args.product, "product.md", root=brand_root.parent)))
        if not product_file:
            sys.exit(f"no product {args.product!r} in {BP.brand_path(brand_root.name, 'products', root=brand_root.parent)}")
    else:
        product_file = read(args.product, required=True) if args.product else ""
    # ONLY WHAT IS FOR SALE TODAY. A product file lists every size the store has
    # ever made; the offer bank lists what is live. Twice the writer sold
    # "2 x The Daily Set — $__" off the product file, a size the store had
    # removed, and twice the price check held the email. A check that keeps
    # catching the same mistake is not the fix: a line in the product file that
    # names a price the bank does not sell today is taken out before any stage
    # sees it, and says so where it stood (2026-09-20).
    if product_file and args.offer and args.offer != "none" and offer_file:
        money = re.compile(r"\$\s?(\d[\d,]*(?:\.\d{2})?)")
        live = {m.replace(",", "") for m in money.findall(offer_file)}
        kept, dropped = [], 0
        for line in product_file.splitlines():
            prices = {m.replace(",", "") for m in money.findall(line)}
            if prices and not prices <= live:
                dropped += 1
                kept.append("- (a size or price not on sale today — removed; sell only what the offer bank lists)")
            else:
                kept.append(line)
        if dropped:
            product_file = "\n".join(kept)
            print(f"     product: {dropped} line(s) naming a price not on sale today removed")
    if not product_file:
        print("     NOTE: no --product — stages are told there is no product "
              "rather than inventing one")
    for name, val in (("avatar", avatar), ("language_bank", language_bank),
                      ("offer_file", offer_file), ("objection_bank", objection_bank),
                      ("hook_ledger", hook_ledger), ("sender_identity", sender_identity)):
        if not val:
            print(f"     NOTE: no {name} for {args.brand} — stages run without it")

    source = read(args.source, required=True)
    formats = render_types(catalogue_path(args.brand))
    source_reference = args.source_reference or Path(args.source).stem
    brand_name = args.brand
    now = datetime.date.today()
    today = f"{now:%A, %-d %B %Y}"

    # THE SEND DAY AND THE MOMENT (RULED 2026-09-10, the owner: "this literally has
    # nothing to do with football"). Both used to stop at the filing layer. The
    # writing stages get them as facts they must obey.
    if args.send_date:
        _d = datetime.date.fromisoformat(args.send_date)
        send_date = (f"{_d:%A, %-d %B %Y}. Write every day-of-the-week and "
                     f"calendar reference against THIS date, never against the "
                     f"swiped email's — the swipe went out on a different day.")
    else:
        send_date = ("(no send date given — then write NO day-of-the-week and no "
                     "calendar reference at all, rather than borrowing the "
                     "swipe's)")
    if args.occasion and not args.occasion.startswith("recorded problem"):
        occasion = (f"`{args.occasion}`. This send exists BECAUSE of this moment "
                    f"— it is why the calendar put it on this day and this is what "
                    f"the reader is living through when it lands. The email must "
                    f"be ABOUT it: the moment is the event the opening reacts to "
                    f"and the world the argument runs through, not a line dropped "
                    f"in near the end. An email that would read identically with "
                    f"the moment deleted has failed this input. If the moment "
                    f"cannot honestly carry this argument, say so in one line "
                    f"rather than writing around it.")
    else:
        occasion = ("(no dated moment — this send was scheduled off a recorded "
                    "problem, so make the argument, not an occasion)")

    # WHAT THE SEND WAS TOLD TO DO, kept beside what it became (2026-09-15).
    # The record used to carry only the source and the stage timings — so the
    # ANGLE, the one line that says what this email argues, existed on the
    # command line and nowhere else. A month of sends could repeat one argument
    # thirteen times and no record anywhere could be asked about it; the way it
    # finally surfaced was a person reading the emails. An assignment that is
    # not written down cannot be checked, and the checks are the whole point.
    state = {
        "slug": label, "label": label, "brand": args.brand,
        "lane_kind": "email",
        "source_path": args.source, "source_reference": source_reference,
        "assignment": {
            "angle": args.angle, "avatar": args.avatar,
            "offer": args.offer, "product": args.product,
            "occasion": args.occasion, "send_date": args.send_date,
            "affiliate": args.affiliate,
        },
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "elements": elements_picked,
        "stages": {},
    }

    def save():
        (out_dir / "run.json").write_text(json.dumps(state, indent=2) + "\n")

    global RERUN_FROM
    if args.rerun_from:
        if args.rerun_from not in SPEC:
            sys.exit(f"--rerun-from wants a stage key: {', '.join(SPEC)}")
        RERUN_FROM = args.rerun_from
    for spec in args.tier:
        name, _, model_name = spec.partition("=")
        if name not in TIERS or not model_name:
            sys.exit(f"--tier wants NAME=MODEL where NAME is one of "
                     f"{', '.join(TIERS)}; got {spec!r}")
        TIERS[name] = model_name

    def MODEL(stage_key):
        """Which model runs this stage. `--model` forces one for the whole
        chain; otherwise the stage's declared tier decides, so the choice
        lives beside the stage it describes rather than at the call site."""
        return args.model or TIERS[SPEC[stage_key]["tier"]]

    # The run records WHICH model wrote each stage (it already records the
    # prompt and its hash). Tiering is a quality bet, and a bet you cannot
    # audit later is a guess: if a stage's output degrades, the record has to
    # be able to say what wrote it.
    state["models"] = {s["key"]: MODEL(s["key"]) for s in STAGES}

    print(f"email chain: {label}  (brand={args.brand})")
    if args.model:
        print(f"      model: {args.model} — forced for every stage")
    else:
        print("     models: " + " · ".join(
            f"{t} ×{sum(1 for s in STAGES if s['tier'] == t)} {TIERS[t].split('-2025')[0]}"
            for t in ("reads", "checks", "designs")))

    # --- read the source ---------------------------------------------------
    roster = (L.avatars(args.brand, BRAND_TREE) if L else None) or []
    roster_txt = "\n".join(
        f"- `{a['key']}` — {a['rows']:,} rows · funnels: "
        + ", ".join(f"{k} {v:,}" for k, v in sorted(a['funnels'].items()) if k)
        + (f" · sub-avatars: {', '.join(a['subs'])}" if a['subs'] else "")
        for a in roster) or "- (this brand has no avatar language banks)"

    # The avatar is a RUN DECLARATION, not something triage infers. Triage may
    # still name a funnel — that is a property of the source, not of the run.
    # The funnel is the SEGMENT's, when the brand's audience matrix says which
    # stage each segment is at — "Core | Lead" is a lead whatever the source
    # email was written to. Triage's reading of the source is the fallback.
    # Without it the language rows came back unfiltered (triage v2 stopped
    # naming a funnel), so a lead and a churned customer got the same voice.
    seg_funnel = None
    try:
        for s in json.loads((brand_root / "email-sms" / "audience-matrix.json").read_text())["segments"]:
            if s.get("name") == args.segment:
                seg_funnel = s.get("funnel")
    except (OSError, ValueError, KeyError):
        pass
    av, funnel = args.avatar, seg_funnel

    def lang(stage):
        """The rows THIS stage needs — queried, never a truncated file."""
        if not args.avatar:
            return ("(this email addresses everyone — no avatar was declared, "
                    "so there is no customer language for it. Write in the "
                    "brand's own voice and make no claim about who is reading.)")
        if not (L and roster):
            return "(this brand has no language bank)"
        return L.for_stage(args.brand, stage, av, funnel, None, 40, BRAND_TREE)

    # THE DRY RUN COMES BEFORE ANY STAGE (2026-09-20). It sat below triage, so
    # every "no model calls" dry run spent one. What only triage can know is
    # reported as "decided at triage".
    if args.dry_run:
        print(f"\n--- dry run: {args.brand} / {args.avatar or 'NO AVATAR (everyone)'} ---")
        rows = [("source", source), ("product_file", product_file),
                ("offer (narrowed)" if args.offer else "offer_file", offer_file),
                ("avatar", avatar), ("language_bank", language_bank),
                ("objection_bank", objection_bank),
                ("proven_angles", proven_angles), ("hook_ledger", hook_ledger),
                ("sender_identity", sender_identity), ("formats", formats)]
        # Where each one was looked for. The table's names are not all keys of
        # the brand map ("offer (narrowed)", "source", "product_file"), so the
        # path column used to come back blank for most rows.
        where = {k: declared.get(k, conventional.get(k)) or "" for k in conventional}
        where["offer (narrowed)"] = where.get("offer_file", "")
        where["source"] = str(args.source)
        where["product_file"] = str(args.product or "")
        where["formats"] = catalogue_path(args.brand).name
        if si.is_file():
            where["sender_identity"] = "email-sms/identity/sender.md"
        if hook_ledger and not brand_file("hook_ledger"):
            where["hook_ledger"] = "email-sms/ledger.md (what the brand has sent — no curated ledger yet)"
        where = {k: v.replace("<avatar>", args.avatar or "<avatar>") for k, v in where.items()}
        ok = 0
        for name, val in rows:
            rel = where.get(name, "")
            if val:
                ok += 1
                print(f"  OK      {name:16} {len(val):>8,} chars   {rel}")
            else:
                print(f"  MISSING {name:16} {'':>8}         {rel or '(no path)'}")
        rst = L.avatars(args.brand, BRAND_TREE) if L else []
        print(f"\n  roster: {', '.join(a['key'] for a in rst) or '(none)'}")
        for a in rst:
            if a["key"] == args.avatar:
                print(f"  {a['key']}: {a['rows']:,} language rows · "
                      f"funnels {', '.join(f'{k} {v:,}' for k, v in sorted(a['funnels'].items()) if k)}")
                if a["subs"]:
                    print(f"  sub-avatars: {', '.join(a['subs'])}")
        for st in ("hooks", "expansion", "close"):
            q = lang(st)          # the same path a real run takes, guard included
            n = q.count("\n") if q else 0
            if not args.avatar:
                print(f"  language query [{st:9}] -> none (addresses everyone)")
            else:
                print(f"  language query [{st:9}] -> {len(q):>7,} chars, ~{n} lines")
        print(f"\n  {ok}/{len(rows)} variables resolved")
        print("\n  decided at triage (step 0 is a model call, so a dry run never makes it):")
        print("    lane · format · sender"
              + ("" if seg_funnel else " · funnel (the segment names none)"))
        if seg_funnel:
            print(f"    funnel: {seg_funnel} — from the segment, not from triage")
        print("\n  would run: " + " · ".join(
            f"{s['id']} {MODEL(s['key']).split('-2025')[0]}" for s in STAGES))
        print(f"  would file to: {out_dir}")
        print("  no model was called and nothing was written.")
        return

    triage = run_stage("stage0", out_dir, MODEL("stage0"), state,
                       today=today, source=source, formats=formats,
                       source_reference=source_reference, avatars=roster_txt,
                       segment=args.segment or "(none declared — a list email, "
                       "no calendar slot named a narrower segment)",
                       awareness_levels=doctrine("awareness")); save()
    lane = _first(LANE_LINE, triage)
    fmt = _first(FORMAT_LINE, triage)
    sender = _first(SENDER_LINE, triage)
    av, funnel = args.avatar, (seg_funnel or _first(FUNNEL_LINE, triage))
    state.update(lane=lane or "unread", format=fmt or "unread",
                 sender=sender or "unread", avatar=av, funnel=funnel)
    print(f"     lane: {lane or '?'} · format: {fmt or '?'} · "
          f"sender: {sender or '?'} · avatar: {av} · funnel: {funnel or '?'}")
    save()

    record = run_stage("stage1", out_dir, MODEL("stage1"), state,
                       today=today, triage=triage, source=source); save()

    spec = run_stage("stage2", out_dir, MODEL("stage2"), state,
                     today=today, triage=triage, record=record); save()
    # the spec step saw the whole record, furniture named and refused; every
    # step from here on gets the message (and the defects list) only
    record = message_only(record)

    # what the brand knows, and which of it THIS source needs
    brand_context = "(no context scout — the copy lane's index is not available)"
    # A run with no --product must not seed None into this set — sorted()
    # over {None, str} is how sep-03 died mid-chain (2026-08-31).
    always = {args.product} if args.product else set()
    if context:
        # Only files that were ACTUALLY loaded. Naming a file here tells the
        # scout not to spend attention on it; naming one that was never read
        # is how a stage ends up with neither the file nor the scout's notice.
        always |= {f"brands/{args.brand}/{rel}"
                   for var, rel in ((v, declared.get(v, conventional.get(v)))
                                    for v in ("avatar", "language_bank",
                                              "objection_bank", "offer_file"))
                   if rel and loaded.get(var)}
        scout = run_stage("stage1b", out_dir, MODEL("stage1b"), state,
                          today=today, triage=triage, spec=spec,
                          context_index=context.index(args.brand, always=always),
                          always_loaded="\n".join(f"- {p}" for p in sorted(always))); save()
        picked = [p for p in context.parse_choice(scout) if p not in always]
        brand_context, used, dropped = context.load(picked)
        state["context"] = {"picked": picked, "chars": used, "dropped": dropped}
        print(f"     context: {len(picked)} file(s), {used:,} chars"
              + (f", {len(dropped)} dropped" if dropped else ""))
        save()

    # --- the week it lands in ----------------------------------------------
    # RULED 2026-09-10: EVERY email gets this, not only the ones on a moment.
    # A moment is a week with things happening in it, and the reader is already
    # inside that week.
    # TWO KINDS OF RESEARCH, and email now gets both (2026-09-19, the owner: "hook
    # up email to the actual customer… and research the chain as well").
    #
    # 1. THE AUDIENCE — the shared research gatherer, the same call the
    #    copywriter makes (tools/copywriter/machine/research.py): the rooms
    #    this avatar actually talks in, what they are saying, and the language
    #    bank's own tagged rows. Email never had it; it had a hand-made file.
    # 2. THE WEEK — a file of this week's facts, when someone has written one.
    #    A file whose date is not this send's date is REFUSED: the September
    #    files were question lists for the calendar's old numbering, and the
    #    Sep 23 email was handed Sep 21's questions for another audience.
    parts = []
    # THIS FILE IS NAMED email.py, and it shadows Python's own `email` package
    # while its folder is on the path. The gatherer's Reddit door needs the
    # real one (urllib -> http.client -> email.parser), so room discovery died
    # with "'email' is not a package" and the research came back with no rooms
    # at all — quietly (first live run, 2026-09-19). Step off the path for the
    # call, and put it back after.
    _saved_path = sys.path[:]
    sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]
    _shadow = sys.modules.get("email")
    if _shadow is not None and not hasattr(_shadow, "__path__"):
        del sys.modules["email"]
    try:
        import research as RS                       # the copywriter's shim — one engine
        audience = RS.text_for(brand=args.brand, avatar=args.avatar, funnel=funnel,
                               out_dir=out_dir, slug=label)
        parts.append("## WHAT THIS AUDIENCE IS SAYING (the research gatherer)\n\n" + audience)
        state["research"] = {"audience_chars": len(audience),
                             "audience_unfilled": audience.startswith("[UNFILLED")}
        print(f"     research: audience {len(audience):,} chars (gatherer)")
    except Exception as e:                          # a research gap is a section, never a stop
        parts.append(f"## WHAT THIS AUDIENCE IS SAYING\n\n[UNFILLED: research gatherer unavailable — {e}]")
        print(f"     research: gatherer UNAVAILABLE ({e})")
    finally:
        sys.path = _saved_path
    if args.research:
        rp = Path(args.research)
        if not rp.is_absolute():
            rp = HERE / rp
        if rp.is_file():
            week = rp.read_text()
            want = ""
            if args.send_date:
                d = datetime.date.fromisoformat(args.send_date)
                want = f"{d.strftime('%A')} {d.day} {d.strftime('%B %Y')}"
            if want and want not in week:
                print(f"     research: {rp.name} REFUSED — it is not about {want}")
                parts.append(f"## THIS WEEK\n\n[UNFILLED: the week file on hand ({rp.name}) "
                             f"was written for another day, not {want}; no week facts for this send]")
            else:
                parts.append("## THIS WEEK\n\n" + week)
                print(f"     research: week file {rp.name} ({len(week):,} chars)")
        else:
            print(f"     NOTE: --research {rp} not found — the live read will say so")
    else:
        parts.append("## THIS WEEK\n\n[UNFILLED: nobody has researched this week yet]")
    research = "\n\n".join(parts)
    # The brand's real tellers and what happened to them (lab/story-builder
    # writes it; every quote checked against the brand's own files).
    story = read(brand_root / "brand-identity" / "story.md") or (
        "(this brand has no story file yet — tell no story you cannot source)")
    market = brand_file("market") or (
        "(this brand has no market file — say so rather than assuming a country)")
    live_read = run_stage("stage1c", out_dir, MODEL("stage1c"), state,
                          today=today, occasion=occasion, send_date=send_date,
                          triage=triage, spec=spec, market=market, avatar=avatar,
                          notable_customers=notable_customers,
                          research=research); save()

    # --- make it ours ------------------------------------------------------
    injection = run_stage("stage3", out_dir, MODEL("stage3"), state,
                          today=today, occasion=occasion, send_date=send_date,
                          live_read=live_read, offer_rule=offer_rule,
                          triage=triage, record=record, spec=spec,
                          brand_context=brand_context, brand_name=brand_name,
                          sender_identity=sender_identity, avatar=avatar,
                          language_bank=language_bank, product_file=product_file,
                          customer_language=lang("injection"),
                          spoken=doctrine("spoken"), story=story,
                          techniques=doctrine("techniques"),
                          angle=args.angle or "(none decided upstream — reason "
                          "from the avatar and language bank alone)",
                          reviewer_note=args.note or "(nobody left one — the plan "
                          "above stands as written)"); save()

    placement = run_stage("stage4", out_dir, MODEL("stage4"), state,
                          today=today, occasion=occasion, send_date=send_date,
                          live_read=live_read, offer_rule=offer_rule,
                          triage=triage, record=record, spec=spec,
                          injection=injection, product_file=product_file,
                          offer_file=offer_file, objection_bank=objection_bank); save()

    subject_set = run_stage("stage5", out_dir, MODEL("stage5"), state,
                            today=today, occasion=occasion, send_date=send_date,
                            live_read=live_read, offer_rule=offer_rule,
                            triage=triage, record=record, spec=spec,
                            injection=injection, placement=placement,
                            sender_identity=sender_identity,
                            language_bank=language_bank,
                            customer_language=lang("hooks"),
                            brand_context=brand_context, hook_ledger=hook_ledger,
                            subject_count=args.subjects,
                            awareness_levels=doctrine("awareness")); save()

    # The gate. An ALREADY AN AD source inherited its structure at injection;
    # building another on top would be two arguments in one email.
    body = injection
    if (lane or "").upper().startswith("ORGANIC"):
        body = run_stage("stage6", out_dir, MODEL("stage6"), state,
                         today=today, triage=triage, spec=spec, injection=injection,
                         placement=placement, product_file=product_file,
                         offer_file=offer_file, language_bank=language_bank,
                         customer_language=lang("expansion"),
                         brand_context=brand_context); save()
    else:
        state["stages"]["stage6"] = {"status": "skipped",
                                     "why": f"lane is {lane or 'unread'} — structure inherited at injection"}
        print("  -- stage6  skipped (lane is not ORGANIC)")
        save()

    close = run_stage("stage7", out_dir, MODEL("stage7"), state,
                      today=today, occasion=occasion, send_date=send_date,
                      live_read=live_read, offer_rule=offer_rule,
                      triage=triage, body=body,
                      sender_identity=sender_identity, spec=spec,
                      placement=placement, product_file=product_file,
                      offer_file=offer_file, language_bank=language_bank,
                      customer_language=lang("close"),
                      brand_context=brand_context,
                      spoken=doctrine("spoken"), story=story); save()

    # --- what ships --------------------------------------------------------
    blocks = run_stage("stage8", out_dir, MODEL("stage8"), state,
                       today=today, occasion=occasion, send_date=send_date,
                       live_read=live_read, offer_rule=offer_rule,
                       triage=triage, record=record, spec=spec,
                       placement=placement, close=close, subject_set=subject_set,
                       product_file=product_file, offer_file=offer_file,
                       language_bank=language_bank, brand_context=brand_context,
                       spoken=doctrine("spoken")); save()

    # THE CHECK — before a person sees it (2026-09-20, the owner: "add in the
    # product facts check… this is all part of copywriting"). The price check
    # and the unfilled check are exact and live in simple_email.py; these three
    # need reading: what the email says the product IS, whether a thought was
    # chopped, and typos. The first rewrite with customer language called the
    # Daily Set "wash, scrub, moisturizer" — it is a serum — and passed every
    # exact check.
    # v2 (2026-09-21) reads the catalogue too, so it can catch a DRAFT product —
    # and so it stops marking a PARTNER's own facts unsupported for being absent
    # from our product file. `offer_rule` already carries both.
    # The check reads EVERY live product, not only the one this send names — an
    # email that ends on a product talks about products the slot never named
    # (2026-09-21), and one product file made every such line "unsupported".
    run_stage("stage8c", out_dir, MODEL("stage8c"), state,
              email=blocks, product_file=BF.catalogue_facts(args.brand, WORKSPACE),
              offer_file=offer_file, offer_rule=offer_rule,
              spoken=doctrine("spoken")); save()

    run_stage("stage9", out_dir, MODEL("stage9"), state,
              today=today, occasion=occasion, send_date=send_date,
              triage=triage, source_reference=source_reference,
              record=record, placement=placement, subject_set=subject_set,
              blocks=blocks, offer_file=offer_file,
              techniques=doctrine("techniques")); save()

    print(f"\ndone -> {out_dir}")
    print(f"build it:  python3 simple_email.py {out_dir} --brand {args.brand}")


if __name__ == "__main__":
    main()
