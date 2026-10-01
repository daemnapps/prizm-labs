#!/usr/bin/env python3
"""The page machine's runner. One swipe page in, one pre-sell page out in our
avatar's words, then one variation per sub-avatar. Every stage is a prompt file
in ../prompts/ with {fields} substituted from the brand's own files; every
prompt-as-sent and every output is kept in runs/<label>/ so the board can show
exactly what ran.

    python3 run.py <page.txt> --brand <brand> --avatar spot-hider \
        --angle pigmentmemory --next select --label scrub-base-01 \
        --source-url https://<competitor>.com/pages/bestfoundation --swipe lps-007 \
        --product brands/<brand>/products/body-scrub.md \
        --offer brands/<brand>/offers/offers.json brands/<brand>/offers/offer-bank.md \
        --subs sun-damage-reckoner clean-only-buyer texture-seeker
        [--dry]      fill every prompt, call nothing — checks the substitution
        [--resume]   reuse what is already in the run folder
        [--no-gate]  skip the copy gate (the check that holds an unfilled note or an unlisted price)
        [--model M]  force one model for every stage (default: each stage's tier)

Gates (machine/page_gates.py): inputs (the signed angle) · elements (the page
format is a real row in the library's format/page — refused otherwise) · copy
(no UNFILLED note, every price one the offer files sell). A held run keeps
everything, says why, and exits 2.

Runs file at the repo root: runs/page-machine/<brand>/<label>/. The old home
beside the code is still read (machine/page_paths.py).

Mirrors copy/machine/copy.py and components/video-teardown/machine/
run.py: same prompt-file-per-stage shape, same headless `claude -p` under the
operator's own login (clean environment — the desktop session's variables make
the child borrow the wrong sign-in), same chatter guard, same retry.

Reads brands/ only. Writes only under runs/.
"""
import argparse, datetime, hashlib, importlib.util, json, os, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_paths as P                                  # noqa: E402
import page_gates as G                                  # noqa: E402

HERE = P.HERE                                           # the tool's own folder
WORKSPACE = P.WORKSPACE                                 # AI_WORKSPACE, else found by walking up
PROMPTS = HERE / "prompts"
RUNS = P.RUNS                                           # runs/page-machine/<brand>/<label>/

# The shared model tiers and the usage-limit signal — components/run-kit.
sys.path.append(str(WORKSPACE / "components" / "run-kit"))
from run_kit import model as KIT                        # noqa: E402
UsageLimit = KIT.UsageLimit

# Borrowed, not copied: the copy machine's brand-context indexer and the
# language-layer engine. Both are the one home for what they do.
sys.path.append(str(WORKSPACE / "components" / "copywriter" / "machine"))
import context as CTX                                   # noqa: E402
CTX.WORKSPACE = WORKSPACE
sys.path.append(str(WORKSPACE / "components" / "language-layer"))
from language_layer import engine as LANG               # noqa: E402

STAGE_USE = {
    "injection": ["problem-language", "self-descriptor", "identity", "tried-and-failed",
                  "alternative-solution", "cope", "why-bought", "post-use-feeling",
                  "what-they-like", "result-language"],
    "close":     ["objection", "refund-reason", "expectation-gap", "comment-objection",
                  "objection-answer", "churn-risk"],
}
LANG.configure(workspace=WORKSPACE, stage_use=STAGE_USE, widen="once",
               title="Customer language for this stage")

# Model per job rides ON the stage (`tier`), so a new stage cannot be missing
# from a second table: `checks` = the reading stages, `designs` = the writing
# ones. The tiers themselves are components/run-kit's (run_kit.model.TIERS).
STAGES = [  # the chain's shape, in one place; board.py reads this too
    dict(key="stage0", tier="checks",   id="0",  name="Triage",        label="triage",    group="READ THE SOURCE",
         blurb="Page job, the classifier's format confirmed, voice, funnel level. Everything downstream binds to it."),
    dict(key="stage1", tier="checks",   id="1",  name="Read",          label="record",    group="READ THE SOURCE",
         blurb="The source page as an objective record — sections, headline, turn, proof, asks, voice, what it never does."),
    dict(key="stage2", tier="designs",  id="2",  name="Spec",          label="spec",      group="READ THE SOURCE",
         blurb="The record abstracted into a brand-free, category-free construct."),
    dict(key="stage2b", tier="checks",  id="2b", name="Context scout", label="context",   group="READ THE SOURCE",
         blurb="Picks what THIS construct needs from everything the brand knows, and says what it left out."),
    dict(key="stage3", tier="designs",  id="3",  name="Injection",     label="injection", group="MAKE IT OURS",
         blurb="Substitution, never rewriting — the construct is the template, the brand's files fill the slots."),
    dict(key="stage4", tier="designs",  id="4",  name="Close",         label="close",     group="MAKE IT OURS",
         blurb="The objection at the flinch, the handoff to the offer page, the base page end to end."),
    dict(key="stage5", tier="designs",  id="5",  name="Variation",     label="variation", group="ONE PER SUB-AVATAR",
         blurb="Same moves, her words — one page per sub-avatar off the base."),
    dict(key="stage6", tier="checks",   id="6",  name="Brief",         label="brief",     group="HAND IT OVER",
         blurb="What the builder opens: manifest, copy in page order, the offer verbatim, what is open."),
    dict(key="stage7", tier="designs",  id="7",  name="Layout",        label="layout",    group="MAKE IT A PAGE",
         blurb="Which library block carries each move, every slot filled from the words, a picture brief per picture slot."),
]
SPEC = {s["key"]: s for s in STAGES}
FORCED_MODEL = None     # --model: one model for every stage


def model_for(stage, prompt_chars=0):
    """(model, why) for a stage: --model wins; else the stage's tier, stepped up
    to the designs model only when the prompt is past a small window."""
    return KIT.pick(SPEC[stage]["tier"], prompt_chars, forced=FORCED_MODEL)


# Kept for layout.py and anything else that read the old table: derived from the
# tiers, never maintained by hand.
MODELS = {s["key"]: KIT.TIERS[s["tier"]] for s in STAGES}

PURE_TEXT = (
    "You are a document generator running headless. There is no person reading "
    "your reply and no conversation. You have no tools and no filesystem; never "
    "attempt to write, save, or publish anything, and never mention tools, "
    "permissions, files, or what you were unable to do. Your entire response IS "
    "the requested document — it is captured verbatim and used directly. Emit "
    "the document and nothing else: no preamble, no summary of what you did, no "
    "closing commentary, no offer to continue.")
CHATTER = ("permission", "this session", "say the word", "scratchpad",
           "let me know", "i'll land", "blocked by", "would you like")


def say(msg):
    print(msg, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]


def latest_prompt(stage):
    found = list(PROMPTS.glob(f"{stage}-*-v*-damon.md"))
    bad = [p.name for p in found if not re.search(r"-v(\d+)-", p.name)]
    if bad:
        sys.exit(f"prompt file(s) without a version number for {stage}: {', '.join(sorted(bad))} — "
                 f"a prompt is named <stage>-<name>-v<N>-damon.md (N a number; the highest wins)")
    hits = sorted(found, key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    if not hits:
        sys.exit(f"no prompt for {stage} in {PROMPTS}")
    return hits[-1]


def fill(template, fields):
    # Unfilled = a field the TEMPLATE names that the runner did not supply.
    # Checked on the template, not the filled text: brand files themselves
    # mention {hook_ledger} and the like, and those are their words, not holes.
    wanted = set(re.findall(r"\{([a-z_]+)\}", template))
    left = sorted(wanted - set(fields))
    out = template
    for name, value in fields.items():
        out = out.replace("{" + name + "}", value if value else "(none supplied)")
    return out, left


def _clean_env():
    keep = ("HOME", "PATH", "TERM", "LOGNAME", "SHELL", "LANG", "LC_ALL", "TMPDIR")
    return {k: os.environ[k] for k in keep if k in os.environ}


def claude(prompt_text, model):
    last = None
    for attempt in (1, 2, 3, 4):
        r = subprocess.run(["claude", "-p", "--model", model, "--allowed-tools", "",
                            "--output-format", "text", "--append-system-prompt", PURE_TEXT],
                           input=prompt_text, capture_output=True, text=True, env=_clean_env())
        body = (r.stdout or "").strip()
        if not r.returncode and body:
            head = body[:400].lower()
            if sum(w in head for w in CHATTER) >= 2:
                raise RuntimeError("the model reported back instead of producing the document — starts: "
                                   + body[:180].replace("\n", " "))
            return body
        last = r
        both = f"{r.stdout}\n{r.stderr}".lower()
        if "limit" in both and ("usage" in both or "spend" in both):
            # out of usage is not a broken stage — waiting 20s and asking again cannot fix it
            raise UsageLimit(f"the account is out of usage on {model}: {(r.stdout or r.stderr).strip()[:240]}")
        why = (r.stderr or r.stdout or "").strip()[:200] or "no output on either stream"
        say(f"     ! attempt {attempt} failed (exit {r.returncode}): {why}")
        time.sleep(20 * attempt)
    sys.exit(f"a stage failed after 4 attempts (exit {last.returncode})\n"
             f"  stderr: {(last.stderr or '').strip()[:400] or '(empty)'}")


def classify(text, slug, url):
    cp = WORKSPACE / "components" / "naming" / "classify_pages.py"
    sp = importlib.util.spec_from_file_location("cp", cp)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m.page_type(dict(slug=slug, title="", text=text, url=url))


def read(rel):
    p = WORKSPACE / rel
    return p.read_text().strip() if p.is_file() else f"(missing: {rel})"


def doctrine(slice_name):
    """A Schwartz doctrine slice, bound by path — never restated in a prompt.
    Rendered by components/marketing-doctrine/render.py from frameworks.json."""
    return read(f"components/marketing-doctrine/slices/{slice_name}.md")


def render_offer(paths):
    parts = []
    for rel in paths:
        p = WORKSPACE / rel
        if p.suffix == ".json":
            parts.append(f"--- {rel} ---\n\n```json\n{json.dumps(json.loads(p.read_text()), indent=1)}\n```")
        else:
            parts.append(f"--- {rel} ---\n\n{p.read_text().strip()}")
    return "\n\n".join(parts)


def avatars_menu(brand):
    root = WORKSPACE / "brands" / brand / "core-avatars"
    lines = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        subs = sorted(x.stem for x in (d / "sub-avatars").glob("*.md")) if (d / "sub-avatars").is_dir() else []
        lang = d / "language"
        funnels = sorted(x.stem for x in lang.rglob("*.json")) if lang.is_dir() else []
        lines.append(f"- `{d.name}` — profile `{d.relative_to(WORKSPACE)}/profile.md`; sub-avatars: {', '.join(subs) or 'none'}; language files: {', '.join(funnels) or 'none'}")
    return "\n".join(lines)


def sub_card_path(brand, avatar, sub):
    d = WORKSPACE / "brands" / brand / "core-avatars" / avatar / "sub-avatars"
    hits = sorted(d.glob(f"*{sub}*.md"))
    return hits[0] if hits else None


def sub_rows(brand, avatar, sub):
    rows = [r for r in LANG.load(brand, avatar) if (r.get("sub") or "") == sub]
    return LANG.render(rows, header=f"Rows tagged `{sub}` · {len(rows)} verbatims") if rows else \
        f"(no rows tagged `{sub}` in the language files — the card's delta is all this sub has)"


def key(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


class Run:
    def __init__(self, a):
        self.a = a
        # a run carries on where it already lives (either home); a new one
        # files at runs/page-machine/<brand>/<label>/
        found = P.find_run(a.label, a.brand)
        if found and (found / "run.json").exists():
            theirs = json.loads((found / "run.json").read_text()).get("brand")
            if theirs and theirs != a.brand:
                sys.exit(f"the label `{a.label}` is already a {theirs} run ({P.rel(found)}) — pick another --label")
        self.dir = found or P.run_dir(a.brand, a.label)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / "run.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {"stages": {}}
        self.state.update(label=a.label, brand=a.brand, avatar=a.avatar, angle=a.angle,
                          funnel=a.funnel, next=a.next, subs=a.subs, source_url=a.source_url,
                          swipe=a.swipe, product=a.product, offer=list(a.offer),
                          started=self.state.get("started") or datetime.datetime.now().isoformat(timespec="seconds"))
        self.reran = set()   # stages that ran this time, so what reads them reruns too

    def save(self):
        self.state["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
        self.state_path.write_text(json.dumps(self.state, indent=1))

    def have(self, name):
        p = self.dir / f"{name}.md"
        return p.read_text().strip() if p.exists() else None

    def stage(self, stage, name, fields, depends=()):
        """Run one stage, or on --resume keep its finished output — but only
        while its prompt is unchanged AND nothing it reads from reran. Bump a
        prompt's version and that stage reruns, and so does everything fed by
        it; a leaf (a brief) reruns alone."""
        spec = SPEC[stage]
        out_path = self.dir / f"{name}--{spec['label']}.md"
        prompt_file = latest_prompt(stage)
        prev = self.state["stages"].get(name, {})
        if self.a.resume and out_path.exists() and prev.get("status") == "done":
            upstream = [d for d in depends if d in self.reran]
            if prev.get("prompt_sha256_12") == sha(prompt_file) and not upstream:
                say(f"  == {name}  (kept from the run folder)")
                return out_path.read_text().strip()
            why = f"prompt changed: {prev.get('prompt_name')} -> {prompt_file.name}" if not upstream else f"reads from {', '.join(upstream)}, which reran"
            say(f"  ~~ {name}  ({why})")
        self.reran.add(name)
        filled, left = fill(prompt_file.read_text(), fields)
        if left:
            sys.exit(f"{name}: unfilled fields in the prompt: {left}")
        (self.dir / f"{name}--sent.md").write_text(filled)
        model, why_model = model_for(stage, len(filled))
        say(f"  -> {name}  ({prompt_file.name} · {model}" + (f" [{why_model}]" if why_model not in ("checks", "designs", "reads") else "")
            + f" · {len(filled):,} chars in)")
        if self.a.dry:
            self.state["stages"][name] = dict(status="dry", model=model, prompt_name=prompt_file.name,
                                              prompt_sha256_12=sha(prompt_file), chars_in=len(filled),
                                              sent=f"{name}--sent.md")
            self.save()
            return f"(dry run — {name} not called)"
        t0 = time.time()
        output = claude(filled, model)
        secs = round(time.time() - t0, 1)
        out_path.write_text(output + "\n")
        self.state["stages"][name] = dict(status="done", seconds=secs, model=model, chars_in=len(filled),
                                          chars_out=len(output), prompt_name=prompt_file.name,
                                          prompt_sha256_12=sha(prompt_file), out=out_path.name,
                                          sent=f"{name}--sent.md")
        self.save()
        say(f"     done in {secs}s, {len(output):,} chars")
        return output


def main(argv=None):
    try:
        return chain(argv)
    except UsageLimit as e:
        # one clear line, no blind retry: every finished stage is in the run
        # folder, and --resume picks up from the first one that is not
        sys.exit(f"STOPPED — {e}\n  nothing is lost: run the same command with --resume once usage is back")


def chain(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="the captured swipe page's page.txt")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", required=True, help="core avatar key, e.g. spot-hider")
    ap.add_argument("--angle", required=True, help="a signed angle id from the brand's strategy/angles.json")
    ap.add_argument("--funnel", required=True, help="the funnel this page is for, e.g. scrub")
    ap.add_argument("--next", required=True, help="the offer page the pre-sell hands off to, e.g. select")
    ap.add_argument("--label", required=True)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--swipe", default="", help="the swipe registry id, e.g. lps-007")
    ap.add_argument("--product", required=True, help="workspace-relative product card")
    ap.add_argument("--offer", nargs="+", default=None,
                    help="workspace-relative offer files (default: the brand's own offers/offer-bank.md)")
    ap.add_argument("--subs", nargs="*", default=[])
    ap.add_argument("--funnel-level", default="prospect")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--resume", action="store_true", help="reuse finished stages in the run folder, until the first whose prompt changed")
    ap.add_argument("--context-drop", nargs="*", default=[], help="path fragments the context scout may not load, e.g. a sister product's card")
    ap.add_argument("--no-gate", action="store_true", help="skip the copy gate (UNFILLED notes, prices against the offer files)")
    ap.add_argument("--model", default=None, help="force one model for every stage (default: each stage's tier)")
    a = ap.parse_args(argv)
    global FORCED_MODEL
    FORCED_MODEL = a.model

    # INPUTS GATE — the angle must be signed; nothing here coins one
    if not (WORKSPACE / "brands" / a.brand).is_dir():
        sys.exit(f"no brand folder brands/{a.brand} in {WORKSPACE}")
    angles_file = WORKSPACE / "brands" / a.brand / "strategy" / "angles.json"
    if not angles_file.is_file():
        sys.exit(f"brands/{a.brand}/strategy/angles.json is missing — an angle is signed there before a page is made from it")
    angles = json.loads(angles_file.read_text())
    signed = {x["id"]: x for x in angles.get("angles", []) if x.get("status") == "active"}
    if a.angle not in signed:
        sys.exit(f"angle `{a.angle}` is not signed active in brands/{a.brand}/strategy/angles.json — signed: {list(signed)}")
    if not a.offer:
        bank = f"brands/{a.brand}/offers/offer-bank.md"
        if not (WORKSPACE / bank).is_file():
            sys.exit(f"no --offer given and {bank} is not on file — every price on the page comes from an offer file")
        a.offer = [bank]

    src_path = Path(a.source).expanduser().resolve()
    source = src_path.read_text(errors="ignore").strip()

    # ELEMENTS GATE — the format is read by the classifier, then looked up in
    # the element library (format/page). Unknown is refused before anything runs.
    fmt = classify(source, src_path.parent.name, a.source_url)
    fmt_row = G.page_format(fmt)

    run = Run(a)
    (run.dir / "source.md").write_text(f"# Source — {a.source_url}\n\nCaptured page text, as read by the chain.\n\n```\n{source}\n```\n")
    page_name = f"{fmt}-{key(a.avatar)}-{key(a.angle)}"
    run.state.update(format=fmt, page_name=page_name)
    run.state.setdefault("elements", {})["format/page"] = dict(
        id=fmt_row["id"], name=fmt_row.get("name"), status=fmt_row.get("status"), source=fmt_row.get("source"))
    run.save()
    say(f"format (classifier): {fmt} · in the library as “{fmt_row.get('name')}” · page: {page_name}")
    say(f"run folder: {P.rel(run.dir)}")

    today = datetime.date.today().isoformat()
    brand_root = f"brands/{a.brand}"
    avatar_file = f"{brand_root}/core-avatars/{a.avatar}/profile.md"
    rules_file = f"{brand_root}/core-avatars/{a.avatar}/language/rules.md"
    always = [avatar_file, rules_file, a.product] + list(a.offer)
    common = dict(today=today, brand_name=a.brand, avatar=a.avatar, angle=a.angle,
                  page_name=page_name, page_next=a.next, format=fmt)

    triage = run.stage("stage0", "stage0", dict(common, source=source, avatars=avatars_menu(a.brand)))
    record = run.stage("stage1", "stage1", dict(common, triage=triage, source=source), depends=["stage0"])
    later = ["stage3", "stage4", "stage6"] + (["stage5"] if a.subs else [])
    downstream = "".join(latest_prompt(k).read_text() for k in later)
    if "{spec}" in downstream:
        spec = run.stage("stage2", "stage2", dict(common, triage=triage, record=record), depends=["stage1"])
    else:
        spec = "(no construct — clean injection: the source page is the template, line for line)"
        say("  -- stage2  skipped: no later stage reads the construct")
    scout = run.stage("stage2b", "stage2b", dict(
        common, concept_brief=f"## TRIAGE\n\n{triage}\n\n## CONSTRUCT\n\n{spec}",
        context_index=CTX.index(a.brand, always=always),
        always_loaded="\n".join(f"- {p}" for p in always),
        research_questions=doctrine("research-questions")), depends=["stage2"])
    picks = [p for p in CTX.parse_choice(scout) if p not in always]
    # a sister product's files never ride along: the product on this page is --product, only
    dropped_by_rule = [p for p in picks if any(f in p for f in a.context_drop)]
    picks = [p for p in picks if p not in dropped_by_rule]
    if dropped_by_rule: say(f"     context: dropped by --context-drop: {dropped_by_rule}")
    brand_context, used, dropped = CTX.load(picks)
    run.state["context_loaded"] = picks; run.state["context_dropped"] = dropped; run.save()
    say(f"     context: {len(picks)} files, {used:,} chars" + (f"; dropped {dropped}" if dropped else ""))

    def lang(stage):
        try:
            # for_stage returns the rendered block, header included (the copy
            # machine passes it straight into the prompt the same way)
            txt = LANG.for_stage(a.brand, stage, a.avatar, a.funnel_level, None)
            return txt if txt and str(txt).strip() else "(no rows)"
        except Exception as e:
            return f"(language query failed: {e})"

    avatar_txt = read(avatar_file); rules_txt = read(rules_file)
    product_txt = read(a.product); offer_txt = render_offer(a.offer)
    injection = run.stage("stage3", "stage3", dict(
        common, triage=triage, spec=spec, record=record, source=source, avatar=avatar_txt, language_bank=rules_txt,
        language=lang("injection"), product_file=product_txt, offer_file=offer_txt,
        brand_context=brand_context, sections=doctrine("sections")), depends=["stage2b"])
    if not a.dry:
        # elements, recorded: the doctrine sections stage 3 says the page carries,
        # looked up in the library (doctrine/section). An unknown one is written
        # down as unknown — it never stops the run.
        carried, unknown = G.sections_carried(injection)
        run.state.setdefault("elements", {})["doctrine/section"] = dict(carried=carried, unknown=unknown)
        run.save()
        if carried or unknown:
            say(f"     sections carried: {', '.join(carried) or 'none read'}"
                + (f" · NOT in the library: {', '.join(unknown)}" if unknown else ""))
    close = run.stage("stage4", "stage4", dict(
        common, triage=triage, injection=injection, spec=spec, source=source, product_file=product_txt,
        offer_file=offer_txt, language_bank=rules_txt, language=lang("close"),
        brand_context=brand_context, offer_close=doctrine("offer-close"),
        verification=doctrine("verification")), depends=["stage3"])

    source_reference = f"{a.source_url} (swipe {a.swipe or 'unregistered'})"
    brief_common = dict(common, triage=triage, source_reference=source_reference, offer_file=offer_txt,
                        page_format=fmt, page_avatar=a.avatar, page_concept=a.angle,
                        page_swipe=f"swipe:landing-pages:{a.swipe}" if a.swipe else a.source_url,
                        techniques=doctrine("techniques"))
    subs_all = ", ".join(x.stem.split("-", 2)[-1] if x else s for s, x in
                         [(s, sub_card_path(a.brand, a.avatar, s)) for s in a.subs]) or "all"
    run.stage("stage6", "stage6", dict(brief_common, body=close, page_subs=f"[{subs_all}]"), depends=["stage4"])

    pieces = [("the base page", close if G.page_part(close).strip() else injection)]
    for sub in a.subs:
        card = sub_card_path(a.brand, a.avatar, sub)
        if not card:
            say(f"  !! no sub-avatar card for {sub} — skipped"); continue
        sub_name = f"{page_name}-{key(sub)}"
        var = run.stage("stage5", f"stage5-{sub}", dict(
            common, page_name=sub_name, triage=triage, spec=spec, body=close,
            sub_card=card.read_text().strip(), sub_language=sub_rows(a.brand, a.avatar, sub),
            language_bank=rules_txt, product_file=product_txt, offer_file=offer_txt), depends=["stage4"])
        run.stage("stage6", f"stage6-{sub}", dict(brief_common, page_name=sub_name, body=var, page_subs=f"[{sub}]"), depends=[f"stage5-{sub}"])
        pieces.append((f"the {sub} variation", var))

    run.state["finished"] = datetime.datetime.now().isoformat(timespec="seconds"); run.save()

    # COPY GATE — after the words are final, before layout or deliver. Everything
    # the run made is already saved; a held run says why and exits 2.
    held = None
    if a.dry:
        say("  -- copy gate: not run on a dry run (there are no words to check)")
    elif a.no_gate:
        say("  -- copy gate: skipped (--no-gate)")
        run.state["gate"] = dict(copy="skipped (--no-gate)"); run.save()
    else:
        Q = G.quality()
        try:
            G.copy_gate(run.dir, pieces, a.brand, a.offer)
            say("  ok copy gate: no unfilled note, every price is one the offer files sell")
            run.state["gate"] = dict(copy="pass"); run.save()
        except Q.Held as e:
            held = e
            run.state["gate"] = dict(copy="HELD", problems=e.problems); run.save()

    subprocess.run([sys.executable, str(HERE / "machine" / "board.py")], capture_output=True)
    if held:
        say(f"\nHELD at the copy gate — everything is saved in {P.rel(run.dir)} (why: check.json):")
        for p in held.problems:
            say(f"  - {p}")
        say("  fix the words or the offer file and run again with --resume; "
            "deliver.py refuses a held run unless --force; --no-gate skips this check")
        sys.exit(2)
    say("run complete: " + P.rel(run.dir))


if __name__ == "__main__":
    main()
