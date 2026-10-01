#!/usr/bin/env python3
"""The swipe machine.

    python3 run.py <video>                    one video, the whole chain
    python3 run.py --queue                    everything in queue/
    python3 run.py <video> --only 4b --redo   re-run one stage after a prompt edit
    python3 run.py <video> --from 5           pick up where a stopped run left off

Every stage writes three things: the output, the exact prompt that was sent,
and its state. The board is rebuilt after every stage, so it fills in live.
"""

import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C
import brand_folders as BF
import library as L

RUNS = C.runs_root()
QUEUE = C.MACHINE / "queue"
TMP = C.MACHINE / ".tmp"

# The CLI runs a full agent that expects to use tools and report to a person.
# Pointed at "produce this document" it narrates instead — stage 5's first run
# returned a progress update about files it could not write and no brief at all.
PURE_TEXT = (
    "You are a document generator running headless. There is no person reading "
    "your reply and no conversation. You have no tools and no filesystem; never "
    "attempt to write, save, or publish anything, and never mention tools, "
    "permissions, files, or what you were unable to do. Your entire response IS "
    "the requested document — it is captured verbatim and used directly. Emit "
    "the document and nothing else: no preamble, no summary of what you did, no "
    "closing commentary, no offer to continue."
)
CHATTER = ("permission", "this session", "say the word", "scratchpad",
           "let me know", "i'll land", "blocked by", "would you like")


def rebuild_board():
    """Always a fresh process, so it picks up the current builder from disk
    rather than a copy loaded into memory when this run started."""
    subprocess.run(["python3", str(C.MACHINE / "board.py")], capture_output=True)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def slug(s, n=40):
    return (re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower() or "x")[:n]


def say(m):
    print(m, flush=True)



def doc_title(st):
    """What the Doc is called in the Drive folder.

    The brief names itself in its own first heading — that is the concept, and
    it is the thing he recognises in a folder list. Brand and creator come off
    the run, never a literal here (rule 4)."""
    concept = ""
    try:
        f = C.runs_root() / st["slug"] / "brief-final.md"
        for line in f.read_text().splitlines():
            if line.startswith("# "):
                concept = line[2:].strip()
                break
    except Exception:
        pass
    who = st.get("creator") or st.get("label") or st["slug"]
    brand = (st.get("brand") or "").strip()
    head = concept or st.get("label") or st["slug"]
    tail = f"{who} · {brand} brief" if brand else f"{who} brief"
    return f"{head} — {tail}"


def update_doc(prev_url, html, title, home):
    """The Doc she already has is the one that gets updated.

    upload_doc matches by NAME in the folder, and the name carries the
    concept. A full re-run can rename the concept — BEC-01 went from "Twice
    a week" to "One tube, four places" on 2026-09-02 — and then a second Doc
    appeared beside the first, which is exactly the pile of half-versions
    Damon does not want in a creator's folder. So when the run already
    holds a Doc link, that file is updated in place, contents and title
    both, and the link she was sent keeps working. Only a run with no Doc
    yet, or one whose Doc has since been trashed, makes a new one."""
    import io
    import drive as _drive
    m = re.search(r"/document/d/([A-Za-z0-9_-]+)", prev_url or "")
    if m:
        try:
            from googleapiclient.http import MediaIoBaseUpload
            svc = _drive.service()
            media = MediaIoBaseUpload(io.BytesIO(Path(html).read_bytes()),
                                      mimetype="text/html", resumable=False)
            f = svc.files().update(fileId=m.group(1), body={"name": title},
                                   media_body=media,
                                   fields="id,webViewLink,trashed",
                                   supportsAllDrives=True).execute()
            if not f.get("trashed"):
                return f["webViewLink"], False
            # Somebody trashed this brief's Doc on purpose — a retired variant
            # of a post that has a newer run. Re-creating it puts a Doc a
            # human removed back in the creator's folder (two came back on
            # 2026-09-05). Leave it trashed and say so.
            say("      the Doc for this run is in the trash — someone retired "
                "it; not re-creating it. Restore it in Drive to bring it back.")
            return prev_url, False
        except Exception as e:
            say(f"      (could not update the Doc she already has — "
                f"{str(e)[:90]}; falling back to the name)")
    return _drive.upload_doc(html, title, home)


def stay_awake():
    """A full chain is close to an hour of model calls. A sleeping laptop kills
    whichever call is in flight — that is how the first run lost stage 4d."""
    if sys.platform != "darwin":
        return
    try:
        subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------- run state

def load(d):
    f = d / "run.json"
    return json.loads(f.read_text()) if f.exists() else None


def save(d, st):
    (d / "run.json").write_text(json.dumps(st, indent=2))


CREATORS = C.WS / "brands"


def brand_media(brand, *parts):
    """A brand image, wherever it actually is.

    Brand media moved to the Drive on 2026-08-31 (workspace rule 3) and the
    Drive mirrors the repo's paths exactly, so the same relative path resolves
    on either side. Repo first — a machine with no mount still finds anything
    left there — then the Drive."""
    def usable(f):
        # An empty directory left behind when the media moved is not a hit —
        # it resolved first and the frames stage then found no product photos
        # at all (2026-08-31).
        if not f.exists():
            return False
        if not f.is_dir():
            return True
        # This function is about MEDIA. The repo keeps the notes beside where
        # the pictures used to be (products/reference/look.md), so "the folder
        # is not empty" wrongly counted as a hit and the frames stage got zero
        # product photos (2026-08-31).
        return any(x.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                   for x in f.iterdir())

    f = (C.WS / "brands" / brand).joinpath(*parts)
    if usable(f):
        return f
    try:
        f = (C.drive_root() / "brands" / brand).joinpath(*parts)
        return f if usable(f) else None
    except Exception:
        return None


def creator_files(brand, handle):
    """A creator's profile and the likeness we are allowed to seed frames from."""
    base = BF.home(CREATORS / brand, "content-creators")   # old: channels/creators
    prof = base / f"{handle}.md"
    face = base / "likeness" / f"{handle}.jpg"
    if not face.exists():
        face = (brand_media(brand, "content-creators", "likeness", f"{handle}.jpg")
                or brand_media(brand, "channels", "creators", "likeness", f"{handle}.jpg"))
    return (prof if prof.exists() else None), (face if face and face.exists() else None)


def cast_files(brand, avatar):
    """The brand's AI cast member for this run's avatar: their canonical
    master (the ONE identity image — the variation rule: never a creator's
    face, never more than one identity reference) and their identity block.

    Found by convention: brands/<brand>/ai-elements/characters/<character>/
    (old name ai-cast/<character>/)
    character.md carries an `- Avatar link:` line naming the avatar it
    embodies, and the master image sits beside it.

    Several cast members can serve one avatar (the swap frame: actors are a
    bank). The character who EMBODIES the avatar leads; `--cast <character>`
    swaps the actor for a run."""
    # ONE brand home (Damon, 2026-09-02): brands merged into
    # brands/ and stopped existing, ahead of production.
    base = BF.home(C.WS / "brands" / brand, "ai-elements/characters")  # old: ai-cast
    cast_rel = base.relative_to(C.WS / "brands" / brand).parts
    base = base if base.is_dir() else None
    if not (avatar and base):
        return []
    matches = []
    for d in sorted(base.iterdir()):
        cm = d / "character.md"
        if not cm.is_file():
            continue
        text = cm.read_text()
        m = re.search(r"^- Avatar link:.*$", text, re.M)
        if not (m and avatar.lower() in m.group(0).lower()):
            continue
        # the master rides beside character.md in the repo when it can, and
        # on the Drive mirror once brand media moved there (rule 3)
        names = ("master-sheet-sm.jpg", "master-sheet.png",
                 "master.jpg", "master.png")
        master = next((d / n for n in names if (d / n).is_file()), None)
        if not master:
            master = next((f for n in names
                           if (f := brand_media(brand, *cast_rel, d.name, n))), None)
        ident, started = [], False
        for line in text.splitlines():     # the FIRST blockquote is the block
            if line.startswith(">"):
                started = True
                ident.append(line.lstrip("> ").strip())
            elif started:
                break
        matches.append((d.name, master, " ".join(ident).strip() or None,
                        "embodied" in text.lower()))
    # The avatar was assigned upstream, so it IS used, every run (Damon,
    # 2026-08-31) — the character that EMBODIES the avatar leads the bank.
    matches.sort(key=lambda m: (not m[3], m[0]))
    return matches



def identity_of(*parts):
    """A trained identity recorded beside a brand asset, if it has one.
    Returns "<url>|<scale>|<trigger>" for frames.py, else None.

    Written by train_identity.py: words in git, weights on fal. A product's
    identity holds colour/shape/logo; a character's or creator's holds the
    person outright (proven 2026-08-31/09-01)."""
    import json as _json
    f = C.WS.joinpath(*parts) / "lora.json"
    if not f.is_file():
        return None
    try:
        rec = _json.loads(f.read_text())
    except Exception:
        return None
    url, trig = rec.get("lora_url"), rec.get("trigger")
    if not (url and trig):
        return None
    # A product's weights carry the packaging, not the scene — a lower scale
    # keeps them from pulling every frame toward a packshot.
    scale = 0.85 if rec.get("kind") == "product" else 1.0
    return f"{url}|{scale}|{trig}", rec


def brand_root_rel(brand):
    for rel in (("brands", brand), ("lab", "damon", "brands", brand)):
        if C.WS.joinpath(*rel).is_dir():
            return rel
    return ("brands", brand)


def snapshot(d, st, from_stage):
    """Keep the previous breakdown before overwriting it.

    Re-running a video used to destroy what it produced last time, so comparing
    a prompt change meant copying folders by hand. Each re-run now files the
    old outputs as a version, and the run records which prompt version made
    each stage — so a breakdown links back to the exact prompts behind it.
    """
    done = {k: v for k, v in st.get("stages", {}).items()
            if v.get("status") in ("done", "skipped")}
    if not done:
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    v = d / "versions" / stamp
    (v).mkdir(parents=True, exist_ok=True)
    for rec in done.values():
        for key in ("out", "sent"):
            f = rec.get(key)
            if f and (d / f).exists():
                dest = v / Path(f).name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(d / f, dest)
    frames = d / "frames" / "frames"
    if frames.exists():
        shutil.copytree(frames, v / "frames", dirs_exist_ok=True)
    if (d / "brief-final.md").exists():
        shutil.copy2(d / "brief-final.md", v / "brief-final.md")
    (v / "version.json").write_text(json.dumps({
        "stamp": stamp,
        "rerun_from": from_stage,
        "prompts": {k: {"name": r.get("prompt_name"), "version": r.get("version")}
                    for k, r in done.items()},
        "stages": {k: {"status": r.get("status"), "seconds": r.get("seconds"),
                       "chars_out": r.get("chars_out"), "out": r.get("out")}
                   for k, r in done.items()},
        "lane": st.get("triage_lane"), "asset_type": st.get("asset_type"),
    }, indent=2))
    return stamp


def open_run(video, label, brand, creator=None):
    # A run with NO source asset — the FRAMEWORK lane, where the ad is composed
    # from a chosen framework rather than swiped (Damon, 2026-09-18). compose.py
    # opens the folder itself and hands it here already built; everything below
    # that touches the file is skipped, and nothing else about a run changes.
    video = Path(video).expanduser().resolve() if video else None
    if video is not None and not video.exists():
        sys.exit(f"no such video: {video}")
    # WHO ran it, and therefore WHICH run this is (VT-4). Damon's own runs get
    # the bare slug they have always had; anyone else's carries their name, so
    # two people tearing down the same video never land in one folder.
    who = C.operator()
    s = C.run_slug(slug(label or video.stem), who)
    d = RUNS / s
    (d / "prompts").mkdir(parents=True, exist_ok=True)
    st = load(d) or dict(slug=s, label=label or (video.stem if video else s),
                         opened=now(), stages={})
    st.update(brand=brand, label=label or st.get("label"), **C.attribution(who))
    if video is not None:
        st["video"] = str(video)
    # Two kinds of run, and they are not interchangeable. A creator run is her
    # own footage: we may cut stills of her. A swipe run is somebody else's ad:
    # we may study it, never put its people on a brief.
    # `framework` is the composed lane and it survives a re-open — a run with
    # no source asset is not swipe research, and only that one value is
    # preserved, so every existing run behaves exactly as it did.
    st["lane"] = ("creator" if creator else
                  "framework" if st.get("lane") == "framework" else "swipe")
    st["creator"] = creator

    if video is None:
        save(d, st)
        return d, st

    # A copy, not a symlink. macOS blocks background processes from reading
    # ~/Downloads, so a link there serves as 404 and the video will not play.
    link = d / ("source" + video.suffix.lower())
    if not link.exists() or link.is_symlink():
        if link.is_symlink():
            link.unlink()
        shutil.copy2(video, link)
    st["source"] = link.name

    poster = d / "poster.jpg"
    if not poster.exists() and shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-ss", "1", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=360:-1", str(poster)], capture_output=True)
    if poster.exists():
        st["poster"] = poster.name
    save(d, st)
    return d, st


MARKET = {
    "lead_desire": "LEAD DESIRE",
    "awareness": "AWARENESS",
    "awareness_must_not": "AWARENESS MUST NOT",
    "sophistication": "SOPHISTICATION",
    "sophistication_leads_with": "SOPHISTICATION LEADS WITH",
    "route_recommended": "ROUTE RECOMMENDED",
    "story": "STORY",
    "teller": "TELLER",
    "story_why": "STORY WHY",
    "route_why": "ROUTE WHY",
}
ROUTES_KNOWN = ("founder", "creator", "ai")


def awareness_must_not(level):
    """The must_not the doctrine slice gives this level key, or None if the
    slice has no such level. Read from the slice so the rule has one home."""
    f = C.WS / "components/marketing-doctrine/slices/awareness.md"
    if not f.is_file():
        return None
    m = re.search(rf"^## .*\(`{re.escape(level)}`\)\s*$(.*?)(?=^## |\Z)", f.read_text(), re.M | re.S)
    if not m:
        return None
    n = re.search(r"\*\*Must NOT:\*\*[ \t]*(.+)$", m.group(1), re.M)
    return n.group(1).strip() if n else None


def market_state_from(text):
    """What stage 1b decided about the market, from its labelled slots.

    Read leniently: 1b is a prompt, its output is prose around a fenced block,
    and a missing label means "not stated", never a failed run. A route it
    does not name, or names as something that is not a route, is simply not a
    recommendation.
    """
    out = {}
    for field, label in MARKET.items():
        m = re.search(rf"^{re.escape(label)}:[ \t]*(.+)$", text or "", re.M | re.I)
        if m:
            v = m.group(1).strip().strip("`").strip()
            if v and not v.startswith("<"):
                out[field] = v
    rr = (out.get("route_recommended") or "").strip().lower()
    rr = rr.split()[0].strip(".,;:`") if rr else ""
    out["route_recommended"] = rr if rr in ROUTES_KNOWN else None
    if not out["route_recommended"]:
        out.pop("route_recommended")
    return out


FENCE = re.compile(r"```[ \t]*([a-zA-Z0-9_+-]*)[ \t]*\r?\n(.*?)```", re.S)


def json_block(text):
    """The last fenced json block in a stage's output, parsed.

    -> (value, None) on success, (None, reason) on failure. A stage output is
    prose around a block, and a model that explains itself after the block is
    normal — so the LAST block wins, and a block fenced with no language tag
    still counts as long as it parses. Never raises: an unparseable answer is
    a finding to record, not a run to lose.
    """
    blocks = FENCE.findall(text or "")
    if not blocks:
        return None, "no fenced block in the output"
    tagged = [b for lang, b in blocks if lang.lower() == "json"]
    why = ""
    for body in reversed(tagged or [b for _, b in blocks]):
        try:
            return json.loads(body), None
        except Exception as e:
            why = why or f"{type(e).__name__}: {e}"
    return None, why or "no fenced block parsed as json"


DOCTRINE_KEYS = ("framework", "crosswalk_row", "sections_carried", "awareness",
                 "sophistication_signature", "mass_desire", "techniques",
                 "mood", "delivery", "unique")


def file_doctrine(d, body):
    """Stage 1c's block, filed as `<run>/doctrine.json` — the row the framework
    bank is compiled from.

    The doctrine read is the point of the stage; losing it to a stray comma
    would mean re-running a video to get a reading we already have in prose.
    So a failure is WRITTEN rather than raised: the file holds the error and
    the raw output, the bank skips the run with a note, and the stage stays
    done because its words are on disk either way.
    """
    f = Path(d) / "doctrine.json"
    got, why = json_block(body)
    if why or not isinstance(got, dict):
        if not why:
            why = f"the block parsed as {type(got).__name__}, not an object"
        f.write_text(json.dumps({"error": why, "raw": (body or "")[-8000:]},
                                indent=2))
        return None, why
    missing = [k for k in DOCTRINE_KEYS if k not in got]
    if missing:
        got["_missing_keys"] = missing
    f.write_text(json.dumps(got, indent=2, ensure_ascii=False))
    return got, (f"block is missing {', '.join(missing)}" if missing else None)


def outputs_so_far(d, st):
    out = {}
    sub = (st.get("route") or {}).get("substitute") or {}
    for key, rec in st["stages"].items():
        if rec.get("status") == "done" and rec.get("out"):
            f = d / rec["out"]
            if f.exists():
                out[key] = f.read_text()
    # a stage the route skipped still gets asked for downstream; hand over the
    # stage it was standing in for rather than failing the run
    for missing, stand_in in C.route_for(st.get("triage_lane"))["substitute"].items():
        if missing not in out and stand_in in out:
            out[missing] = out[stand_in]
    return out


# ---------------------------------------------------------------- engines

# A dropped connection used to end a run outright: KZN-07 died at Hooks on
# 2026-08-27 with "Connection lost mid-response" and had to be restarted by
# hand. Everything else in this chain degrades — frames fall back to a smaller
# model then to a still, the Doc skips and says so, a spent Apify key switches
# accounts — but a network blip on any of the eleven thinking stages just
# stopped. Over dozens of videos that is a certainty, usually unattended.
#
# Only TRANSIENT failures retry. A prompt that produces a bad answer produces
# the same bad answer three times over and burns three Opus calls doing it, so
# anything not on this list still stops the stage immediately.
TRANSIENT = (
    "connection lost", "connection reset", "connection aborted", "broken pipe",
    "timed out", "timeout", "temporarily", "overloaded", "unavailable",
    "econnreset", "eof occurred", "incomplete", "try again",
    "rate limit", "429", "500", "502", "503", "504",
)


def transient(err):
    e = str(err).lower()
    return any(m in e for m in TRANSIENT)


def with_retry(fn, what, tries=5, wait=30):
    """Run an engine call, riding out a blip. Reports every retry — a stage
    that silently took five attempts is a stage nobody knows is flaky.

    Five tries backing off 30/60/90/120s covers about five minutes. A provider
    outage is measured in minutes, not seconds: Gemini answered 503 for longer
    than the first version's 60-second budget and killed a run that would have
    survived a slightly more patient one."""
    last = None
    for n in range(1, tries + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            if n == tries or not transient(e):
                raise
            # The LAST line of a traceback is the actual exception; the first
            # 70 characters are "p:\n  File ..." and say nothing. Reporting
            # the head made a plain 503 look like a mystery (2026-08-28).
            msg = [l for l in str(e).strip().splitlines() if l.strip()]
            msg = msg[-1].strip() if msg else str(e)[:70]
            say(f"      {what} hit a blip ({msg[:90]}) — "
                f"retry {n} of {tries - 1} in {wait * n}s")
            time.sleep(wait * n)
    raise last


def gemini_video(prompt_path, video, out):
    """Read the video. If the best model is busy, use the next one that can.

    A 503 "high demand" from Gemini is not this machine's fault and not
    something waiting five minutes reliably fixes — but a second model usually
    answers straight away. Reports which model actually read the video, because
    a brief built by the second-best model is a fact about that brief."""
    last = ""
    for i, model in enumerate([C.GEMINI_MODEL] + list(getattr(C, "GEMINI_FALLBACKS", []))):
        r = subprocess.run(["python3", str(C.CM / "tools" / "gemini_breakdown.py"),
                            str(video), "--prompt-file", str(prompt_path),
                            "--model", model, "--out", str(out)],
                           capture_output=True, text=True)
        if not r.returncode and out.exists():
            if i:
                say(f"      {C.GEMINI_MODEL} was busy — read by {model} instead")
            return model
        last = (r.stderr or r.stdout or "gemini failed")[-1200:]
        if "high demand" not in last and "503" not in last and "UNAVAILABLE" not in last:
            break            # a real error: another model will fail the same way
    raise RuntimeError(last)


def gemini_text(prompt_path, out):
    r = subprocess.run(["python3", str(C.CM / "tools" / "gemini_text.py"),
                        "--prompt-file", str(prompt_path),
                        "--model", C.GEMINI_MODEL, "--out", str(out)],
                       capture_output=True, text=True)
    if r.returncode or not out.exists():
        raise RuntimeError((r.stderr or r.stdout or "gemini failed")[-1200:])
    return C.GEMINI_MODEL


def _clean_env():
    """The machine's own login, never the session's.

    When a run is started from inside a Claude desktop session, the child
    `claude -p` inherits that session's CLAUDE_CODE_* variables and tries to
    borrow the desktop's sign-in instead of its own — and when the desktop's
    token is the one that has lapsed, every stage fails with "OAuth session
    expired" even though `claude auth status` from a plain shell says logged
    in (2026-09-03, five runs stopped this way). Strip those variables so the
    subprocess authenticates the way it does from Terminal."""
    # Stripping only the CLAUDE_* variables was not enough — something else
    # the desktop session exports still steers the sign-in (2026-09-03). A
    # plain environment is what Terminal gives, and that one works.
    # USER is deliberately NOT passed: with the desktop session's USER value
    # the CLI looks up the wrong keychain entry and reports the session
    # expired; without it, it finds its own login (bisected 2026-09-03).
    keep = ("HOME", "PATH", "TERM", "LOGNAME", "SHELL", "LANG", "LC_ALL",
            "TMPDIR")
    return {k: os.environ[k] for k in keep if k in os.environ}


def claude(prompt_text, out):
    r = subprocess.run(["claude", "-p", "--model", C.CLAUDE_MODEL,
                        "--allowed-tools", "", "--append-system-prompt", PURE_TEXT],
                       input=prompt_text, capture_output=True, text=True,
                       cwd=str(C.MACHINE), env=_clean_env())
    if r.returncode or not r.stdout.strip():
        raise RuntimeError((r.stderr or r.stdout or "claude failed")[-1200:])
    body = r.stdout
    head = body[:400].lower()
    if sum(w in head for w in CHATTER) >= 2:
        raise RuntimeError("the model reported back instead of producing the "
                           "document — starts: " + body[:180].replace("\n", " "))
    # The tail check has to be narrow. Scanning the last 400 characters killed a
    # perfectly good hook set whose closing line was a ledger note: these
    # phrases appear inside real content all the time. Only a short, final,
    # first-person line addressed to a reader is commentary.
    lines = [l.strip() for l in body.strip().splitlines() if l.strip()]
    last = lines[-1].lower() if lines else ""
    conversational = (
        len(last) < 200
        and any(w in last for w in CHATTER)
        and any(last.startswith(p) for p in
                ("say the word", "let me know", "i'll ", "i can ", "would you",
                 "happy to", "just say", "want me"))
    )
    if conversational:
        raise RuntimeError("the document ends by talking to a reader rather "
                           "than with content — last line: " + lines[-1][:180])
    out.write_text(body)
    return C.CLAUDE_MODEL


def frames(stage, d, st, vars_, out):
    """Stage 6 is not a text call — it cuts stills from her own video and only
    generates what the video does not contain, so its inputs go in as arguments
    rather than pasted into a prompt."""
    brief_rec = st["stages"].get("stage5")
    if not brief_rec or brief_rec.get("status") != "done":
        raise RuntimeError("stage 5 has to finish first — frames go onto its brief")
    brief = d / brief_rec["out"]
    # Damon's runner, not the shared one: every scene gets a frame, none dropped.
    tool = C.MACHINE / "frames.py"
    work = d / "frames"
    work.mkdir(exist_ok=True)
    copy = work / "brief.md"
    copy.write_text(brief.read_text())
    # who is on camera, read out of the teardown. Without this the image model
    # invents a different woman for every scene.
    # The teardown opens with a Character & Setting Profile whose first entry
    # is the person on camera, physically described: "Caucasian female, blonde
    # shoulder-length wavy hair. Natural makeup look."
    #
    # The old pattern matched the word "Character" anywhere and took the next
    # 40-320 characters, so it lifted the PSYCHOLOGY archetype instead — every
    # frame was told "the person is The Relatable Survivor. Signals: casual
    # home setting, messy vanity" — a persona, not a face. Given that, the
    # model invented a different woman on every frame (2026-08-25).
    subject = ""
    rec = st["stages"].get("stage1") or {}
    if rec.get("out") and (d / rec["out"]).exists():
        import re as _re
        t = (d / rec["out"]).read_text()
        # first cast entry after the Characters heading, whatever it is called
        m = _re.search(
            r"\*\*Characters?:?\*\*\s*\n\s*\*\s*\*\*([^*]+?)\*\*[:\s]*(.{20,240})",
            t, _re.S)
        if m:
            who, look = m.group(1).strip().rstrip(":"), m.group(2)
            # an image model cannot draw an accent; drop the audio half
            look = _re.split(r"\bVoice\b\s*:", look)[0]
            look = " ".join(look.split()).rstrip(" .*-–—")
            if len(look) >= 20:
                subject = f"{look}. The same person appears in every frame."
    if not subject:
        say("      NOTE: no physical description of the subject found — "
            "frames may not hold one consistent person")

    # The teardown records the source's own caption styling ("Text Overlay:
    # White sans-serif font, bottom-center"). Until 2026-08-25 the frame
    # generator used a hardcoded guess instead, so captions came back in a
    # different style from the format being swiped — and varied frame to
    # frame. Read the real one.
    caption_style = ""
    if rec.get("out") and (d / rec["out"]).exists():
        import re as _re
        m = _re.search(r"\*\*Text Overlays?:?\*\*\s*(.{10,160})",
                       (d / rec["out"]).read_text())
        if m:
            caption_style = " ".join(
                m.group(1).split("(")[0].split()).rstrip(" .*-–—")

    cmd = ["python3", str(tool), "--brief", str(copy), "--video", str(st["video"]),
           "--out", str(work / "frames")]
    if subject:
        cmd += ["--subject", subject]
    if caption_style:
        cmd += ["--caption-style", caption_style]
        say(f"      caption style from the source: {caption_style}")
    if vars_.get("product_look"):
        cmd += ["--product-look", vars_["product_look"]]
    # The brand keeps real product photography beside its product file, and
    # that file rules that anything picturing the product takes its look from
    # there. Until 2026-08-25 only the written description was passed, so the
    # model imagined the packaging and invented labels. Hand over the actual
    # photographs. Brand-agnostic: the folder is found by convention, never
    # named here (workspace rule 7).
    # No brand fallback. Defaulting to a named brand here would quietly hand
    # one brand's product photography to another brand's run — the exact
    # failure the brand-agnostic rule exists to stop. No brand, no photos.
    brand_name = st.get("brand")
    # THE RUN'S OWN PRODUCT FIRST (2026-08-31): the flat products/reference/
    # folder predates products-as-folders and held two lifestyle shots — one
    # showing TWO products at once — so the model redrew the logo per frame
    # from the worst possible references while six clean packshots sat in the
    # product's own images/ folder, unread. Clean packshots lead: the label
    # is learned from the shot whose whole job is the label.
    ref = None
    prod = (st.get("product") or "").strip().lower()
    if brand_name and prod:
        ref = brand_media(brand_name, "products", prod, "images")
    if brand_name and not ref:
        ref = brand_media(brand_name, "products", "reference")
    shots = sorted((p for p in ref.glob("*")
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")),
                   key=lambda p: (not p.name.lower().startswith("packshot"),
                                  p.name)) \
        if ref and ref.is_dir() else []
    for p in shots[:4]:          # Pro accepts 6 object references
        cmd += ["--product-image", str(p)]
    if shots:
        say(f"      product reference: {len(shots[:4])} real photo(s) — "
            + ", ".join(p.name for p in shots[:4]))
    # TRAINED IDENTITIES ARE PARKED (Damon, 2026-09-02). They solved identity
    # consistency, which edit-first now solves better — the source frame
    # carries the person. And they actively FIGHT a style conversion: a LoRA
    # trained on photoreal images encodes "photoreal", so asking it for an
    # animated look fights its own training (four failed attempts, same day).
    # The lora.json records stay on disk; nothing reads them unless asked.
    use_ids = bool(st.get("use_identities"))
    if use_ids and brand_name and prod:
        got = identity_of(*brand_root_rel(brand_name), "products", prod)
        if got:
            cmd += ["--identity", got[0]]
            say(f"      TRAINED IDENTITY: {prod} — the packaging is trained "
                "in; a label-forward frame still composites the real packshot")
    # Likeness seeding restored 2026-08-25 (Damon): the mock-ups are of the
    # creator, so her face has to be in them. It was removed on 08-21 after the
    # seed still and the anchor fought over who the person was; the fix is that
    # they no longer both answer that question — the still owns the room, the
    # anchor owns her (see SEED_RELATIONSHIP_WITH_FACE in frames.py).
    # Brand-agnostic: found by convention from the brand and the handle.
    if st.get("creator"):
        _, face = creator_files(st["brand"], st["creator"])
        root = brand_root_rel(st["brand"])
        cc = BF.home(C.WS.joinpath(*root), "content-creators").relative_to(C.WS.joinpath(*root)).parts
        got = (identity_of(*root, *cc, st["creator"])
               or identity_of(*root, "creators", st["creator"])) if use_ids else None
        if got:
            cmd += ["--identity", got[0]]
            say(f"      TRAINED IDENTITY: {st['creator']} — generated with "
                f"her own trained identity (trained {got[1].get('trained')})")
        elif face:
            cmd += ["--face", str(face)]
            say(f"      likeness anchor: {face.name}")
        else:
            say(f"      NO likeness anchor for {st['creator']} — the frames will "
                f"show someone who merely fits the description. Cut one from her "
                f"own video into brands/{st['brand']}/content-creators/likeness/")
    elif st.get("production_route") == "ai":
        # The AI route casts from the brand's AI cast, bound to the avatar
        # stage 1b assigned — the assignment is used, every run. Same identity
        # discipline as the character boards: exactly one identity image, the
        # character's own canonical master. `--cast <name>` swaps the actor.
        aud = st.get("audience") or {}
        matches = cast_files(st["brand"],
                             aud.get("_avatar") or aud.get("avatar"))
        want = (st.get("cast") or "").lower()
        picked = next((m for m in matches if m[0].lower() == want), None) \
            if want else (matches[0] if matches else None)
        if picked and picked[1]:
            who, master, ident, _ = picked
            root = brand_root_rel(st["brand"])
            ch = BF.home(C.WS.joinpath(*root), "ai-elements/characters").relative_to(C.WS.joinpath(*root)).parts
            got = identity_of(*root, *ch, who) if use_ids else None
            if got:
                cmd += ["--identity", got[0]]
                say(f"      TRAINED IDENTITY: {who} — generated with her "
                    f"identity trained in (trained {got[1].get('trained')})")
            else:
                cmd += ["--face", str(master)]
            if ident and "--subject" not in cmd:
                cmd += ["--subject", ident]
            others = ", ".join(m[0] for m in matches if m[0] != who)
            say(f"      cast: {who} — this avatar's cast member, their "
                f"canonical master as the one identity image"
                + (f" (also castable: {others} — rerun with --cast)" if others else ""))
        else:
            say("      NO cast anchor — no AI character links to this "
                "run's avatar, so every frame will invent its own person. "
                f"Cast one in brands/{st['brand']}/ai-elements/characters/")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(C.MACHINE))
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout or "frames failed")[-1200:])
    say("      " + (r.stdout.strip().splitlines() or [""])[-1])
    out.write_text(copy.read_text())
    # Was hardcoded "gemini-3-pro-image" while frames.py actually ran the lite
    # model — so every board entry named a model that had not drawn anything.
    # Ask the tool what it really used (fixed 2026-08-25).
    import frames as _frames
    return _frames.MODEL


TIMES = C.MACHINE / "stage-times.json"


def record_time(key, seconds):
    """Keep how long each stage really takes, so the board can show an honest
    progress bar instead of a spinner that tells him nothing."""
    try:
        d = json.loads(TIMES.read_text()) if TIMES.exists() else {}
    except Exception:
        d = {}
    d.setdefault(key, []).append(seconds)
    d[key] = d[key][-12:]
    _write_times(d)


def _write_times(d):
    """Read-modify-write on a file every run shares. Unlocked, two runs
    finishing a stage at the same moment lose one of the entries — harmless
    for one video at a time, wrong the moment several run in parallel, which
    is the plan. Costs nothing; take the lock.

    Only the estimate is at stake, never a brief, so a lock we cannot get is a
    skipped write rather than a failed run."""
    import fcntl
    try:
        TIMES.touch(exist_ok=True)
        with open(TIMES, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                cur = json.loads(f.read() or "{}")
            except Exception:
                cur = {}
            for k, v in d.items():
                cur[k] = v[-12:]
            f.seek(0); f.truncate()
            f.write(json.dumps(cur, indent=2))
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass


def expected():
    try:
        d = json.loads(TIMES.read_text()) if TIMES.exists() else {}
    except Exception:
        return {}
    return {k: round(sorted(v)[len(v) // 2], 1) for k, v in d.items() if v}


# v18 renamed the unit Scene -> Frame. Both accepted, and the label is
# echoed back verbatim so the filled brief keeps the wording the prompt used.
SLOT = re.compile(r"^!\[(Frame|Scene|Opening) (\d+)\]\(—\)\s*$", re.M)


SAY = re.compile(r"^>?\s*\*\*Say:?\*\*\s*(.+?)\s*$", re.M)

# A line with no words in it. The brief writes these as directions, and a
# creator reading a transcript needs the beat marked, not the stage direction.
NO_LINE = ("nothing", "none", "n/a", "-", "—", "nothing — picture only",
           "nothing - picture only", "no line", "silent")


def transcript(brief):
    """Every spoken line, in order, on its own.

    Damon, 2026-08-26: a creator should not have to read a shot list to find
    out what to say. Built here rather than asked of stage 5 because the lines
    already exist — lifting them is mechanical, and a model asked to repeat
    itself paraphrases. This way the transcript cannot drift from the frames.
    """
    # Only the shot list. The openings section offers six alternate versions of
    # the same first line — real lines, but options, and reading them one after
    # another as a script says "I ran into my ex husband" six times.
    m = re.search(r"^##+\s*The frames\b.*$", brief, re.M)
    body = brief[m.end():] if m else brief
    said = []
    for raw in SAY.findall(body):
        line = raw.strip().strip("*").strip()
        bare = line.strip('"“”').strip().lower().rstrip(".")
        if not line or bare in NO_LINE or bare.startswith("nothing"):
            said.append(None)          # a held beat, kept so the order reads true
        else:
            said.append(line.strip('"“”').strip())
    if not any(said):
        return ""
    # Two documents, not one. WHAT TO FILM is read while setting up; this is
    # read with the camera running. The heading pairs with the shot list's,
    # and the rule below keeps the instruction from running into the first
    # spoken line — without it the whole section reads as one block and a
    # maker either says the instruction out loud or scrolls past the script.
    out = ["", "---", "", "## WHAT TO SAY", "",
           "Every line in order, nothing else. The frames above say how to "
           "film them; this is only what to say.", "", "---", ""]
    silent = 0
    for line in said:
        if line is None:
            silent += 1
            continue
        if silent:
            out.append(f"*({silent} beat{'s' if silent > 1 else ''} with no line)*")
            out.append("")
            silent = 0
        out.append(line)
        out.append("")
    return "\n".join(out)


GENERAL = "GENERAL — any creator"


def brief_count(st):
    """How many briefs this creator has — every run of hers that reached a
    final brief, this one included. A swipe run has no creator and counts
    itself alone."""
    who = st.get("creator")
    n = 0
    for rd in RUNS.iterdir():
        f = rd / "run.json"
        if not f.is_file():
            continue
        try:
            o = json.loads(f.read_text())
        except Exception:
            continue
        same = (o.get("creator") == who) if who else (
            not o.get("creator") and o.get("brand") == st.get("brand")
            and o.get("lane") == "swipe")
        if same and (rd / "brief-final.md").is_file():
            n += 1
    return max(n, 1)


CARD = re.compile(r"^\*\*On screen:?\*\*\s*(.+?)\s*$", re.M)


def script_block(spec):
    """The whole script in order, for the page — read as-is or said her way.

    Spoken formats: every Say line from the shot list, in order, held beats
    marked. Card formats (nothing spoken): every distinct on-screen card, in
    order. Lifted mechanically from the spec, never rewritten."""
    m = re.search(r"^##+\s*The frames\b.*$", spec, re.M)
    body = spec[m.end():] if m else spec
    lines, silent = [], 0
    for raw in SAY.findall(body):
        line = raw.strip().strip("*").strip()
        bare = line.strip('"“”').strip().lower().rstrip(".")
        if not line or bare in NO_LINE or bare.startswith("nothing"):
            silent += 1
            continue
        if silent:
            lines.append(f"*({silent} beat{'s' if silent > 1 else ''} with no line)*")
            silent = 0
        lines.append(line.strip('"“”').strip())
    head = ("## The script, straight through\n\n"
            "Read it as-is if you'd rather, or say it your way — the lines are "
            "in order, one per beat. Keep the product points above; everything "
            "else is yours.\n")
    if lines:
        return head + "\n" + "\n\n".join(lines) + "\n"
    cards, seen = [], set()
    for raw in CARD.findall(body):
        c = raw.strip().strip('"“”').strip()
        if not c or c.lower() in ("nothing", "none", "n/a", "-") or c in seen:
            continue
        seen.add(c); cards.append(c)
    if cards:
        return ("## The cards, straight through\n\n"
                "Nothing is spoken in this format — these are the words on "
                "screen, in order.\n\n" + "\n\n".join(cards) + "\n")
    return ""


def inject(stage, d, st, out):
    """Stage 7 — put stage 6's pictures into the shot list, and produce the one
    file that goes to the maker. It fills slots; it writes nothing."""
    b = st["stages"].get("stage5")
    if not b or b.get("status") != "done":
        raise RuntimeError("there is no brief to put pictures into — stage 5 first")
    frames_dir = d / "frames" / "frames"
    brief = (d / b["out"]).read_text()

    # A scene is identified by concept AND number: three concepts each restart
    # at Scene 1, so matching on the number alone collapses them.
    concept = 0
    lines, filled, dropped = [], 0, 0
    for line in brief.split("\n"):
        if line.startswith("# "):
            concept += 1
        m = SLOT.match(line)
        if not m:
            lines.append(line)
            continue
        # group 1 is the word (Frame, Scene or Opening); group 2 the number.
        letter = "o" if m.group(1) == "Opening" else "s"
        key = f"c{max(concept,1)}{letter}{int(m.group(2)):02d}"
        hit = None
        for ext in (".jpg", ".png", ".jpeg", ".webp"):
            cand = frames_dir / f"{key}{ext}"
            if cand.exists():
                hit = cand
                break
        if hit:
            rel = os.path.relpath(hit, d)
            lines.append(f"![{m.group(1)} {m.group(2)}]({rel})")
            filled += 1
        else:
            # no picture means no slot — an empty box reads as something missing
            dropped += 1
    final = "\n".join(lines) + transcript(brief)
    out.write_text(final)
    (d / "brief-final.md").write_text(final)

    # If the brief points at a Drive copy, that one file has to be readable by
    # whoever receives the brief. Recorded per brief, not applied in bulk —
    # link-sharing is public, so it is switched on for the file that actually
    # goes out and nothing else.
    url = source_url(Path(st["video"])) if st.get("video") else ""
    st["origin_url"] = origin_url(Path(st["video"])) if st.get("video") else ""
    if "drive.google.com" in url:
        fid = drive_id(Path(st["video"]))
        st["needs_share"] = dict(file_id=fid, url=url, done=False)
        say(f"      this brief links to Drive — file {fid} needs link-sharing on")
    else:
        st.pop("needs_share", None)
    say(f"      {filled} pictures placed, {dropped} scenes left without one")
    return f"{filled} placed / {dropped} without"


# ---------------------------------------------------------------- one stage

def run_stage(d, st, stage, extras, redo=False):
    key, sid = stage["key"], stage["id"]
    rec = st["stages"].get(key, {})
    if rec.get("status") == "done" and not redo:
        say(f"  {sid:<3} {stage['name']:<11} already done")
        return True

    if not stage["prompt"]:
        st["stages"][key] = dict(status="error", name=stage["name"],
                                 error="no prompt file found for this stage",
                                 finished=now())
        save(d, st)
        say(f"  {sid:<3} {stage['name']:<11} NO PROMPT")
        return False

    ppath = Path(stage["prompt"])
    template = ppath.read_text()

    st["stages"][key] = dict(status="running", name=stage["name"],
                             prompt_file=str(ppath), prompt_name=ppath.name,
                             version=stage["version"], engine=stage["engine"],
                             started=now())
    save(d, st)
    say(f"  {sid:<3} {stage['name']:<11} running  ({ppath.name})")

    t0 = time.time()
    # Fourteen numbered files loose in the run folder buried the one document
    # anyone opens (Damon, 2026-08-27). They go in stages/. The name recorded
    # on the run stays relative to the run folder, which is how every reader
    # already resolves it — `d / rec["out"]` keeps working untouched.
    out_name = f"stages/{sid}-{slug(stage['name'])}.md"
    out = d / out_name
    out.parent.mkdir(parents=True, exist_ok=True)
    sent = d / "prompts" / Path(out_name).name
    TMP.mkdir(exist_ok=True)

    try:
        pack = dict(extras)
        pack["source_url"] = (source_url(Path(st["video"]))
                              if st.get("video") else "") or "NONE"
        # Who stage 1b decided this run speaks to. The brand's variables map
        # resolves every avatar-shaped path through it, so without this the
        # map's <avatar> rows can never fill and the chain silently falls back
        # to the config's conventional path — which is how briefs were written
        # from a two-week-old avatar while the run record said "spot-hider".
        _av = (st.get("audience") or {}).get("_avatar")
        if _av:
            pack["avatar"] = _av
        pack.update(outputs_so_far(d, st))
        # Stage 1b decided who this run speaks to; every ?query after it
        # inherits that, so the rows a stage sees are this avatar's, in this
        # funnel, about this subject.
        pack.update(st.get("audience") or {})
        # Stage 8 reads across runs and records, which the config's variable
        # language cannot express — creator_profile.py gathers her record,
        # her teardown history and the brand's own spec, and the config binds
        # them as ~vars.
        if stage.get("role") == "profile":
            import creator_profile as _cp
            pack.update(_cp.inputs(st))
        # The page (7b) tells her how many documents are in her folder, so
        # "do I do just one of these?" is answered on the sheet itself.
        if stage.get("role") == "page":
            pack["brief_count"] = str(brief_count(st))
        # ~research — the gatherer, resolved the way every other ~var is.
        # Nobody decides to research: the chain does it because the variable
        # is in the wiring. It NEVER blocks a run — no gatherer, no key or a
        # refused source and the stage runs clean on [UNFILLED], which is what
        # the prompts are written to expect.
        if any(v == "~research" for v in (stage.get("vars") or {}).values()):
            try:
                import research as _rs
                got = _rs.inputs(st)
                if isinstance(got, dict):
                    pack.update({k: v for k, v in got.items() if v})
            except Exception as e:
                say(f"      research: unavailable ({type(e).__name__}) — running clean")
            pack.setdefault("research",
                            "[UNFILLED: research gatherer not available]")
        # ~voiceprint — the brand's measured creator voiceprints (Damon,
        # 2026-09-19: "analyze the audio specifically and create voice
        # prints"). brands/<brand>/content-creators/VOICEPRINTS.md (old: creators/), written by
        # `gather.py voiceprint`, keyed per avatar and sub-avatar; the spoken
        # script matches its rhythm. A brand with none runs on the register
        # recipe alone and the stage is told so — never a stopped run.
        if any(v == "~voiceprint" for v in (stage.get("vars") or {}).values()):
            vf = BF.home(C.WS / "brands" / st["brand"], "content-creators") / "VOICEPRINTS.md"
            if not vf.is_file():
                vf = C.WS / "brands" / st["brand"] / "creators" / "VOICEPRINTS.md"
            pack["voiceprint"] = (vf.read_text() if vf.is_file() else
                                  "[UNFILLED: no creator voiceprints on file for this "
                                  "brand — `gather.py voiceprint --brand <brand> --all` "
                                  "measures them off the creators' own audio]")
        # ~story — the brand's storytelling framework beside its position
        # (Damon, 2026-09-19: "storytelling and intent over volume").
        # brands/<brand>/brand-identity/story.md (old: story.md); after 1b has picked, the pick is appended
        # so every later stage tells the same story in the same teller's
        # mouth. A brand with none runs as before — never a stopped run.
        if any(v == "~story" for v in (stage.get("vars") or {}).values()):
            sf = BF.home(C.WS / "brands" / st["brand"], "brand-identity/story.md")
            if sf.is_file():
                txt = sf.read_text()
                ms = st.get("market_state") or {}
                if ms.get("story"):
                    txt += ("\n\n---\nTHIS RUN'S STORY (picked at 1b): STORY: "
                            + ms["story"] + " · TELLER: " + (ms.get("teller") or "none")
                            + (" · WHY: " + ms["story_why"] if ms.get("story_why") else "") + "\n")
                pack["story"] = txt
            else:
                pack["story"] = ("[UNFILLED: this brand has no story.md yet — "
                                 "`python3 story-builder/build.py --brand <brand>` drafts one]")
        # per-run bindings win over anything the shared config pins
        if st.get("creator"):
            prof, _ = creator_files(st["brand"], st["creator"])
            if prof:
                pack["_creator_profile"] = prof.read_text()
        for var in stage.get("per_run", []):
            if var == "creator_profile" and "_creator_profile" in pack:
                stage = {**stage, "vars": {**stage["vars"], var: "=" + pack["_creator_profile"]}}
            elif var == "creator_profile" and st.get("lane") == "swipe":
                stage = {**stage, "vars": {**stage["vars"], var:
                    "=UNASSIGNED. This brief is written to no one. It came from swipe "
                    "research, not from any creator's own page. Never name a creator, "
                    "never reference their habits, their posts or their style."}}
        filled_vars, sources = {}, {}
        for var, src in stage["vars"].items():
            # A run with --no-frames has no stage 6; the assemble stage then
            # takes the brief as it is, every picture slot empty. No pictures
            # reach the creator's Doc any more (2026-09-18), so the general
            # briefs run without frames and stop needing them here.
            if src == "@stage6" and "stage6" not in pack:
                filled_vars[var], sources[var] = "NONE — frames not run", "no frames"
                continue
            # The variables/ convention (Damon, 2026-08-31): a brand's own
            # variables/video.md outranks the chain config's conventional
            # path for any variable it names. Avatar-shaped rows resolve
            # only once stage 1b has decided who the run speaks to; before
            # that, the config's default stands.
            rel = _brand_video_map(st["brand"]).get(var)
            if rel:
                if "<avatar>" in rel:
                    _av = (st.get("audience") or {}).get("avatar")
                    rel = rel.replace("<avatar>", _av) if _av else None
                if rel:
                    cand = C.WS / "brands" / st["brand"] / rel
                    if cand.exists():
                        src = f"brands/{st['brand']}/{rel}"
            text, origin = C.resolve_source(src, st["brand"], pack, var=var)
            filled_vars[var], sources[var] = text, origin

        asks = set(re.findall(r"\{([a-z0-9_]+)\}", template))
        missing = sorted(asks - set(filled_vars))
        if missing and stage["engine"] != "frames":
            raise RuntimeError("the chain config doesn't supply: " + ", ".join(missing))

        filled = template
        for var, text in filled_vars.items():
            filled = filled.replace("{" + var + "}", text)
        sent.write_text(filled)

        # frames has its own model fallback and its own per-frame retries, so
        # it is left alone; the rest ride out a blip (see with_retry).
        label = stage["name"]
        if stage["engine"] == "gemini-video":
            model = with_retry(lambda: gemini_video(ppath, Path(st["video"]), out), label)
        elif stage["engine"] == "gemini-text":
            tmp = TMP / f"{st['slug']}-{sid}.md"
            tmp.write_text(filled)
            model = with_retry(lambda: gemini_text(tmp, out), label)
        elif stage["engine"] == "inject":
            model = inject(stage, d, st, out)
        elif stage["engine"] == "control":
            # 3v — the proven ad's own script as the baseline (Variation video)
            import control as _ctl
            model = _ctl.file_control(d, st, out)
        elif stage["engine"] == "mark-used":
            # 5u — the language this asset used, marked in the used lane
            import mark_used as _mu
            model = _mu.run(d, st, out)
        elif stage["engine"] == "frames":
            model = frames(stage, d, st, filled_vars, out)
        else:
            model = with_retry(lambda: claude(filled, out), label)

        body = re.sub(r"^<!--.*?-->\n\n", "", out.read_text(), count=1, flags=re.S)
        out.write_text(body)

        st["stages"][key] = dict(
            status="done", name=stage["name"], prompt_file=str(ppath),
            prompt_name=ppath.name, version=stage["version"],
            engine=stage["engine"], model=model, started=rec.get("started") or now(),
            finished=now(), seconds=round(time.time() - t0, 1), out=out_name,
            sent="prompts/" + Path(out_name).name, chars_out=len(body), sources=sources)
        say(f"  {sid:<3} {stage['name']:<11} done in {round(time.time()-t0)}s "
            f"— {len(body):,} chars")

        if key == "stage7b":
            # The straight script, lifted from the spec so it cannot drift
            # from the frames (Damon, 2026-09-03; kept 2026-09-18: "we still
            # want the script"). v5's concept has no pictures, so the block
            # simply closes the document.
            spec = ""
            rec7 = st["stages"].get("stage7") or {}
            if rec7.get("out") and (d / rec7["out"]).exists():
                spec = (d / rec7["out"]).read_text()
            block = script_block(spec)
            if block:
                marker = "## How it might look"
                if marker in body:
                    body = body.replace(marker, block + "\n" + marker, 1)
                else:
                    body = body.rstrip() + "\n\n" + block
                out.write_text(body)
        if key == "stage1c":
            # The doctrine read of the SOURCE, banked (Damon's ruling
            # 2026-09-18). The prose output stays the record a person reads;
            # this is the machine-readable row framework_bank.py compiles, so
            # the unique framework behind a swipe outlives the one brief it
            # was torn down for. Never fatal — see file_doctrine().
            try:
                got, note = file_doctrine(d, body)
            except Exception as e:
                got, note = None, f"{type(e).__name__}: {e}"
            if got:
                st["doctrine"] = {k: got.get(k) for k in
                                  ("framework", "crosswalk_row", "awareness",
                                   "sophistication_signature", "unique")}
                aw = got.get("awareness") if isinstance(got.get("awareness"), dict) else {}
                say("      doctrine: "
                    + " · ".join(x for x in (
                        got.get("framework"),
                        (f"{aw.get('entry')}→{aw.get('exit')}"
                         if aw.get("entry") or aw.get("exit") else ""),
                        got.get("sophistication_signature"),
                    ) if x))
            if note:
                st.setdefault("doctrine_note", note)
                say(f"      doctrine block not clean — {note[:120]}")
            # The labels just filed, checked against the shared element
            # library (2026-09-20) -> <run>/elements.json. An unknown value
            # is recorded as unknown and the run goes on: it is evidence of a
            # missing row, never a reason to stop. Costs nothing — two JSON
            # reads. Off with VT_NO_ELEMENTS_CHECK=1.
            if got:
                try:
                    import elements_check as _ec
                    rep, enote = _ec.check_run(d)
                    if rep:
                        st["elements"] = rep["counts"]
                        say(f"      elements: {enote}")
                except Exception as e:
                    say(f"      elements: SKIPPED — {str(e)[:100]}")
        if key == "stage1b":
            aud = C.audience_from(body)
            # A declared audience is a slot, not a suggestion: whatever 1b
            # printed, the run speaks to who it was declared for (2026-09-20).
            if extras.get("declared_avatar"):
                aud["_avatar"] = extras["declared_avatar"]
                aud["_sub_avatar"] = extras.get("declared_sub") or None
                st["declared_audience"] = {"avatar": extras["declared_avatar"],
                                           "sub": extras.get("declared_sub") or None}
            st["audience"] = aud
            # What 1b decided about the MARKET, kept beside what it decided
            # about the reader (Damon's ruling 2026-09-18). The lead desire,
            # the awareness level and the sophistication stage are read by
            # every writing stage after this one through the doctrine slices;
            # the run records them so a finished run says what market it was
            # written for without anyone re-reading the stage output.
            ms = market_state_from(body)
            # A declared awareness is a slot too (2026-09-20). Every writing
            # stage reads 1b's own text, so when 1b printed another rung the
            # two labelled lines are corrected IN the stage output, with the
            # level's must_not quoted from the doctrine slice — never invented.
            dec_aw = (extras.get("declared_awareness") or "").strip().lower()
            if dec_aw:
                must_not = awareness_must_not(dec_aw)
                if must_not is None:
                    say(f"      declared awareness '{dec_aw}' is not a level in the slice — ignored")
                else:
                    if (ms.get("awareness") or "").strip().lower() != dec_aw:
                        say(f"      awareness: 1b said {ms.get('awareness')!r}, declared {dec_aw!r} — declared holds")
                    body = re.sub(r"^AWARENESS:[ \t]*.*$", f"AWARENESS: {dec_aw}", body, count=1, flags=re.M)
                    body = re.sub(r"^AWARENESS MUST NOT:[ \t]*.*$",
                                  f'AWARENESS MUST NOT: "{must_not}"', body, count=1, flags=re.M)
                    out.write_text(body)
                    ms["awareness"], ms["awareness_must_not"] = dec_aw, must_not
                    st.setdefault("declared_audience", {})["awareness"] = dec_aw
            if ms:
                st["market_state"] = ms
                say("      market: "
                    + " · ".join(f"{k} {v}" for k, v in (
                        ("desire", ms.get("lead_desire")),
                        ("awareness", ms.get("awareness")),
                        ("stage", ms.get("sophistication")),
                    ) if v))
            # The route recommended by 1b, for a run that did not name one.
            # The default used to be a silent "creator" nobody chose.
            rr = (ms or {}).get("route_recommended")
            if rr and not st.get("route_chosen_by_hand"):
                if st.get("production_route") != rr:
                    say(f"      lane: {rr} — recommended by 1b"
                        + (f" ({ms.get('route_why')})" if ms.get("route_why") else ""))
                st["production_route"] = rr
            av, fn = aud.get("_avatar"), aud.get("_funnel")
            tp = ", ".join(aud.get("_topics") or []) or "none"
            say(f"      avatar: {av or 'NONE FIT'} · funnel: {fn or '?'} · topics: {tp}")
            # A run that cannot say who it is for should stop and say so. Every
            # stage after this would otherwise draw its words from every avatar
            # at once and look fine doing it.
            if not av:
                raise RuntimeError(
                    "no avatar fits this source — stage 1b said so, and the "
                    "stages after it would each pull language from every avatar "
                    "this brand has. Add an avatar this source belongs to, or "
                    "re-run pointed at a brand that owns this subject.")
        ok = True
    except Exception as e:
        st["stages"][key] = dict(
            status="error", name=stage["name"], prompt_file=str(ppath),
            prompt_name=ppath.name, version=stage["version"],
            engine=stage["engine"], started=rec.get("started") or now(),
            finished=now(), seconds=round(time.time() - t0, 1),
            sent="prompts/" + Path(out_name).name if sent.exists() else None,
            error=str(e)[-1800:])
        say(f"  {sid:<3} {stage['name']:<11} STOPPED — {str(e)[:140]}")
        ok = False

    # The My Feeds library is a shelf of SOURCES. A composed run has none, so
    # there is nothing to file there and nothing has gone wrong.
    # A Variation video run's source is already on the shelf (the proven ad's
    # own teardown); its tree of runs is filed with the tree, not the library.
    if ok and st.get("video") and not st.get("variation_of"):
        try:
            home = library_home(Path(st["video"]), st["slug"], st)
            home.mkdir(parents=True, exist_ok=True)
            idx = home / ("post.md" if (home / "post.md").exists() else "asset.md")
            if not idx.exists():
                idx.write_text(f"# {st['label']}\n\n"
                               f"**Source** {st['video']}  \n"
                               f"**Brand** {st['brand']}  \n"
                               f"**Lane** {st.get('triage_lane') or 'unclassified'}  \n"
                               f"**Swiped** {L.now()}\n")
            L.save_teardown(home, sid, stage["name"], stage["version"],
                            (d / out_name).read_text(), ppath.name)
            st["library"] = str(home)
        except Exception as e:
            say(f"      (couldn't file it in the library: {str(e)[:70]})")
    if ok and key == "stage4a":
        verdict = C.product_entry((d / out_name).read_text())
        if verdict == "NONE":
            st["asset_type"] = "hook-asset"
            say("      product entry: NONE — this hands off, so the brief "
                "becomes a hook asset, not an ad")
        elif verdict:
            st["asset_type"] = ""
            say(f"      product entry: {verdict}")
        else:
            say("      (4a printed no verdict line — brief stays an ad)")
    if ok and stage.get("role") == "profile":
        # The stage wrote its output into the run like any other; landing it
        # where the brand keeps profiles is the point of the stage. A landing
        # that fails is recorded on the stage, never swallowed.
        try:
            import creator_profile as _cp
            dest = _cp.publish(st, (d / out_name).read_text())
            st["profile"] = str(dest)
            say(f"      her profile refreshed — {dest}")
        except Exception as e:
            st["stages"][key]["publish_error"] = str(e)[:400]
            say(f"      written in the run but NOT landed in the brand: {str(e)[:120]}")
    if ok and key == "stage0":
        st["triage_lane"] = C.lane_from_triage((d / out_name).read_text())
        say(f"      lane: {st['triage_lane']}")
        # Record the routing the moment triage decides it. run_video reads the
        # lane BEFORE the plan starts, so on a first clean run there is nothing
        # to read yet — the lane only took effect on a second invocation. For
        # ORGANIC that was invisible (it skips nothing), but an ALREADY AN AD
        # source is supposed to skip Expansion, and on a first run it did not:
        # it got the whole build-from-nothing treatment its structure already
        # had. Found 2026-08-28 by asking why `route` was empty on the runs
        # that finished in one go.
        r = C.route_for(st["triage_lane"])
        st["route"] = dict(lane=st["triage_lane"], why=r["why"],
                           skipped=r["skip"] if r["skip"] else [])
    if ok:
        record_time(key, round(time.time() - t0, 1))
    save(d, st)
    return ok


def file_to_repo(d):
    """13. The run's WORDS, filed to the repo's one home for run records —
    runs/video-teardown/<brand>/<slug>/ (runs/README.md; added 2026-09-20).
    A COPY: machine/runs/<slug>/ stays the working folder the board and the
    Drive mirror read, and nothing is moved. Text only, nothing over 1 MB.
    Never fatal — a filing that fails prints SKIPPED and the run is whole.
    Off with VT_NO_REPO_FILING=1."""
    try:
        import file_run as _fr
        note = _fr.file_after_run(d)
        if note:
            say(f"  13  Repo record {note}")
    except Exception as e:
        say(f"  13  Repo record SKIPPED — {str(e)[:120]}")


_VIDEO_MAPS = {}

def _brand_video_map(brand):
    """The brand's variables/video.md as {var: rel-path}. Parsed once,
    tolerant of both `avatar` and `{avatar}` styles; an absent map means
    the chain config's conventional paths stand untouched."""
    if brand not in _VIDEO_MAPS:
        rows = {}
        f = C.WS / "brands" / brand / "variables" / "video.md"
        if f.is_file():
            for m in re.finditer(r"^\s*\|?\s*`\{?([a-z_]+)\}?`\s*\|\s*`([^`]+)`",
                                 f.read_text(), re.M):
                rows[m.group(1)] = m.group(2)
            if rows:
                say(f"      brand map: variables/video.md ({len(rows)} vars)")
        _VIDEO_MAPS[brand] = rows
    return _VIDEO_MAPS[brand]


def run_video(video, label, brand, only=None, start=None, stop=None,
              redo=False, extras=None, creator=None, want_frames=True,
              route=None, cast=None, product=None,
              use_identities=False):
    d, st = open_run(video, label, brand, creator=creator)
    if cast:
        st["cast"] = cast.lower()
    st["use_identities"] = bool(use_identities)
    if product:
        st["product"] = product.lower()
    # The production route is a per-run decision — founder, creator or ai —
    # never the config's (it pins "=creator", which is how nothing ever
    # reached the ai lane). Default: creator, the original brief. It picks
    # the stage-5 brief and fills {production_route} at stages 3 and 5.
    if route:
        st["production_route"] = route.lower()
        st["route_chosen_by_hand"] = True
    elif (st.get("market_state") or {}).get("route_recommended"):
        # --route was not given, but 1b has already run and recommended one.
        # In Claude Code this printed line is the yes/no nobody has to answer.
        st["production_route"] = st["market_state"]["route_recommended"]
        st["route_chosen_by_hand"] = False
    st.setdefault("production_route", "creator")
    prod_route = st["production_route"]
    why_route = ("chosen" if st.get("route_chosen_by_hand") else
                 "recommended by 1b" if (st.get("market_state") or {}).get(
                     "route_recommended") == prod_route else "the default")
    if not st.get("triage_lane"):
        rec = st["stages"].get("stage0") or {}
        if rec.get("status") == "done" and rec.get("out"):
            f = d / rec["out"]
            if f.exists():
                st["triage_lane"] = C.lane_from_triage(f.read_text())
    say(f"\n▶ {st['label']}  ({brand})"
        + (f"  ·  {st['triage_lane']}" if st.get("triage_lane") else "")
        + f"  ·  via {prod_route} ({why_route})")
    plan = C.stages(brand, st.get("asset_type", ""), prod_route,
                st.get("triage_lane") or "")

    # what stage 0 decided about this video now decides what runs.
    # On a first run the lane is not known yet — triage is the first stage of
    # the plan below — so this block only bites on a resume. The plan loop
    # re-checks after stage 0 (see "the lane may only now be known").
    lane = st.get("triage_lane")
    route = C.route_for(lane)
    if lane:
        if route["skip"] is None:
            say(f"  lane: {lane} — {route['why']}")
            say("  not running the video chain on this one.")
            st["route"] = dict(lane=lane, why=route["why"], skipped=["everything"])
            save(d, st)
            return False
        if route["skip"] and not only:
            say(f"  lane: {lane} — {route['why']}")
            say(f"  skipping {', '.join(route['skip'])}")
            # record it as skipped, with the reason. "Waiting" reads as still
            # coming, which is the opposite of what happened.
            for s in plan:
                if s["key"] in route["skip"]:
                    # A stage the run already holds an output for is NOT
                    # skipped — it was stood in for before the chain started
                    # (compose.py does exactly this on the FRAMEWORK lane).
                    # Overwriting it would throw the stand-in away and take
                    # every `@stage` that reads it down with it.
                    if (st["stages"].get(s["key"]) or {}).get("status") == "done":
                        continue
                    st["stages"][s["key"]] = dict(
                        status="skipped", name=s["name"], engine=s["engine"],
                        version=s["version"], prompt_file=s["prompt"],
                        prompt_name=Path(s["prompt"]).name if s["prompt"] else "",
                        why=f"{lane} — {route['why']}", finished=now())
            plan = [s for s in plan if s["key"] not in route["skip"]]
        st["route"] = dict(lane=lane, why=route["why"], skipped=route["skip"])
        save(d, st)

    # Pre-flight: is this source actually moving? Cheap, and it would have
    # stopped KZN-07 (a before/after photo) before five stages ran. It reports
    # and never gates — no stage checks whether a format SHOULD be replicated
    # and that call is Damon's (2026-08-20).
    if not only and not start:
        try:
            import motion as _motion
            m = _motion.check(Path(st["video"]))   # no video -> caught below
            if m["verdict"] == "still":
                say(f"      NOTE: this source barely moves ({m['movement']}) — "
                    f"very likely a still or a text card posted as a reel. "
                    f"Running anyway; expect a thin brief.")
            st["motion"] = m
            save(d, st)
        except Exception:
            pass

    if not want_frames and not only:
        plan = [s for s in plan if s["engine"] != "frames"]
    ids = [s["id"] for s in plan]
    if only:
        plan = [s for s in plan if s["id"] in only]
    else:
        if start:
            plan = plan[ids.index(start):]
        if stop:
            k = [s["id"] for s in plan]
            plan = plan[:k.index(stop) + 1]
    # Anything about to be redone stops claiming it is done. Stale "done"
    # badges from the previous run made finished-looking stages that had not
    # started yet.
    if redo:
        for x in plan:
            rec = st["stages"].get(x["key"])
            if rec and rec.get("status") in ("done", "error"):
                st["stages"][x["key"]] = dict(status="waiting", name=x["name"],
                                              engine=x["engine"], version=x["version"])
        save(d, st)

    # anything about to be rebuilt gets filed as a version first
    if (redo or start) and any(
            st["stages"].get(x["key"], {}).get("status") in ("done", "skipped")
            for x in plan):
        stamp = snapshot(d, st, start or (only[0] if only else "all"))
        if stamp:
            say(f"  previous breakdown filed as version {stamp}")
            save(d, st)

    skipped_by_lane = set()
    # The production route may only be known once 1b has run — it recommends
    # one, and a run that did not name one takes it. The plan was built before
    # that, so the stages after 1b are re-resolved against the route actually
    # chosen; anything the new route drops is recorded skipped rather than
    # silently run.
    replan, route_dropped = {}, set()
    for s in plan:
        # The lane may only now be known: on a first run triage IS the first
        # stage in this loop, so the routing above had nothing to read. Honour
        # it here or an ALREADY AN AD source gets Expansion run on it anyway.
        if s["key"] in skipped_by_lane:
            continue
        if s["key"] in route_dropped:
            st["stages"][s["key"]] = dict(
                status="skipped", name=s["name"], engine=s["engine"],
                version=s["version"], prompt_file=s["prompt"],
                prompt_name=Path(s["prompt"]).name if s["prompt"] else "",
                why=f"the {prod_route} route does not use this stage",
                finished=now())
            save(d, st)
            say(f"  {s['id']:<3} {s['name']:<11} skipped — the {prod_route} "
                f"route does not use it")
            continue
        if s["key"] in replan:
            s = replan[s["key"]]
        if s["key"] == "stage5" and st.get("asset_type") == "hook-asset":
            s = next(x for x in C.stages(brand, "hook-asset",
                                         st.get("production_route", ""),
                                         st.get("triage_lane") or "")
                     if x["key"] == "stage5")
        # The profile refresh only means something on a creator's own run,
        # and only for a brand that has said where profiles live. Anything
        # else is recorded skipped, with the reason, so the board never shows
        # a stage silently missing.
        if s.get("role") == "profile":
            import creator_profile as _cp
            why = _cp.skip_reason(st)
            if why:
                st["stages"][s["key"]] = dict(
                    status="skipped", name=s["name"], engine=s["engine"],
                    version=s["version"], prompt_file=s["prompt"],
                    prompt_name=Path(s["prompt"]).name if s["prompt"] else "",
                    why=why, finished=now())
                save(d, st)
                say(f"  {s['id']:<3} {s['name']:<11} skipped — {why}")
                continue
        if not run_stage(d, st, s, extras or {}, redo=redo):
            # A brief is never lost to a profile: stage 8 failing leaves the
            # run going — the Doc still gets made — and says how to re-run it.
            if s.get("role") == "profile":
                say(f"  {s['id']:<3} {s['name']:<11} FAILED — the run continues; "
                    f"re-run it alone with --only {s['id']}")
                continue
            say(f"  stopped at {s['id']} — fix it and re-run with --from {s['id']}")
            return False
        if s["key"] == "stage1b" and not only \
                and st.get("production_route") != prod_route:
            prod_route = st["production_route"]
            fresh = {x["key"]: x for x in
                     C.stages(brand, st.get("asset_type", ""), prod_route,
                              st.get("triage_lane") or "")}
            replan = fresh
            route_dropped = {x["key"] for x in plan} - set(fresh)
            save(d, st)
            say(f"  lane: {prod_route} — the rest of this run follows 1b")
        if s["key"] == "stage0" and not only:
            r = C.route_for(st.get("triage_lane"))
            if r["skip"] is None:
                say(f"  lane: {st.get('triage_lane')} — {r['why']}")
                say("  not running the video chain on this one.")
                save(d, st)
                return False
            if r["skip"]:
                say(f"  skipping {', '.join(r['skip'])} — {r['why']}")
                skipped_by_lane = set(r["skip"])
                for x in plan:
                    if x["key"] in skipped_by_lane:
                        st["stages"][x["key"]] = dict(
                            status="skipped", name=x["name"], engine=x["engine"],
                            version=x["version"], prompt_file=x["prompt"],
                            prompt_name=Path(x["prompt"]).name if x["prompt"] else "",
                            why=f"{st.get('triage_lane')} — {r['why']}",
                            finished=now())
                save(d, st)
    # Last step: the brief as a document, not a markdown file. It is the only
    # form anyone outside this machine actually opens, so it is part of a run
    # finishing rather than something remembered afterwards. Mirroring first is
    # what gives every frame a Drive id, which is what lets the document show
    # its pictures. Never fatal — the run's own outputs are already safe on
    # disk, and a Drive that is unmounted or still syncing is a wait, not a
    # failure.
    if stop and not (Path(d) / "stages" / "7-final-brief.md").is_file() \
            and not (Path(d) / "7-final-brief.md").is_file():
        # still mirror the record to the Drive — words travel even when no
        # document was asked for
        try:
            C.mirror_to_drive(st["slug"])
        except Exception as e:
            say(f"      record not mirrored yet ({e}) — it is safe on disk")
        # A run stopped early still read the source, so its doctrine read is
        # still worth banking — the bank is about the swipe, not the brief.
        try:
            import framework_bank as _fb
            _fb.refresh()
        except Exception:
            pass
        file_to_repo(d)
        say(f"  ✔ records run — stopped at {stop} as asked; no document for a "
            "run that wrote no brief")
        return True
    try:
        import gdoc as _gdoc
        dest, mirror_err = None, None
        try:
            dest = C.mirror_to_drive(st["slug"])
            st.pop("mirror_error", None)
        except C.MountError as e:
            # The run keeps going — its words are safe on this disk. What must
            # not happen is finishing quietly: the LOSS goes on the run so the
            # records plane can say this one never reached the team.
            mirror_err = e
            C.record_mirror_error(d, st, e)
        # Drive hands back a file's id only once IT has finished taking the
        # upload, which is seconds AFTER the copy returns. Asking immediately
        # gets nothing, and a document with no ids is a document of empty red
        # boxes — which is exactly what KZN-03 and KZN-04 came out as on
        # 2026-08-27. gdoc.py's own CLI has always waited here; this path did
        # not, so a run through run.py produced a brief with no pictures in it.
        n_frames = 0
        fdir = d / "frames" / "frames"
        if fdir.is_dir():
            n_frames = len([f for f in fdir.iterdir()
                            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")])
        ids = {}
        if dest:
            for attempt in range(12):
                ids = _gdoc.ids_from_drive(st["slug"])
                if not n_frames or len(ids) >= n_frames:
                    break
                if attempt == 0:
                    say(f"      waiting for the Drive to hand back picture ids "
                        f"({len(ids)}/{n_frames}) …")
                time.sleep(15)
        out, placed, missing = _gdoc.build(st["slug"], ids)
        st["gdoc_html"] = out.name
        save(d, st)
        # Second pass: the document and the updated run.json were both written
        # after the first mirror, so neither is on the Drive yet.
        if dest:
            C.mirror_to_drive(st["slug"])
        say(f"  9   Document    {out.name} — {placed} picture(s) placed"
            + (f", {len(missing)} still syncing" if missing else ""))
        if mirror_err:
            say(f"      NOT MIRRORED — {str(mirror_err)[:160]}")
            say("      this run is on this laptop only; recorded on the run "
                "as mirror_error")
    except Exception as e:
        say(f"  9   Document    SKIPPED — {str(e)[:120]}")

    # 10. The Doc itself. The document step only lays out a file; until 2026-08-26 a
    # session had to create the Doc by hand, and a run whose session forgot
    # ended with nothing anyone could open. The service account closes it.
    # Same name in the same folder updates in place, so a re-run does not
    # strand the link he already has beside a second copy.
    try:
        import drive as _drive
        doc_dir = C.run_mirror_dir(st["slug"])
        # The mirror has only just been written, so the folder's Drive id can
        # take a moment to appear in the extended attribute. Checking once and
        # giving up left KZN-03 with no Doc at all on 2026-08-27 — the whole
        # point of this stage. Wait for it the way gdoc.py waits for frames.
        parent = ""
        for attempt in range(10):
            parent = _drive.folder_id(doc_dir)
            if parent:
                break
            if attempt == 0:
                say("  10  Doc         waiting for the Drive to sync this run …")
            time.sleep(6)
        if not parent:
            say("  10  Doc         SKIPPED — the Drive never synced this run")
        else:
            # The Doc goes in one folder per creator, not in the run folder.
            # Damon shares that folder with his content manager, who passes it
            # straight to the creator — so it holds finished briefs and
            # nothing else (2026-08-28). The run folder keeps the working
            # files, which nobody outside needs to see.
            try:
                # A swipe run written to no one is a GENERAL brief — any
                # creator can film it (Damon, 2026-09-18). It goes in the
                # brand's own shared folder beside the creators' folders.
                sh = _drive.creator_share(st.get("creator") or GENERAL, brand=st["brand"])
            except Exception as e:
                sh = None
                say(f"      (could not set up her folder: {str(e)[:70]})")
            home = sh["briefs"] if sh else parent
            # The video the brief was built on goes up FIRST, so the brief
            # can end with a link to it (Damon, 2026-09-18). Straight through
            # the API, never via the mount.
            vurl = ""
            import simplify as _simp
            try:
                vurl, vnew = _simp.inspiration_video(Path(d), st, home)
                if vurl:
                    st["video_url"] = vurl
                    save(d, st)
                    say(f"  10a Video       {'uploaded' if vnew else 'in place'} — {vurl}")
            except Exception as e:
                say(f"  10a Video       SKIPPED — {str(e)[:100]}")
            if vurl:
                out, _, _ = _gdoc.build(st["slug"], ids, tail=_simp.example_link(vurl))
                st["gdoc_html"] = out.name
            url, made = update_doc(st.get("gdoc_url") or "",
                                   Path(d) / st["gdoc_html"], doc_title(st), home)
            st["gdoc_url"] = url
            save(d, st)
            say(f"  10  Doc         {'created' if made else 'updated'} — {url}")
            if sh:
                st["creator_folder"] = sh["link"]
                say(f"      her folder: {sh['link']}")
            # Her folder opens with one Start-here Doc — the brand's four
            # shared sections (Christine, 2026-09-18) — refreshed on every
            # run so its count of briefs stays right.
            if sh:
                try:
                    surl, snew = _simp.start_here(st["brand"], st.get("creator") or "", home)
                    st["start_here_url"] = surl
                    save(d, st)
                    say(f"  10b Start here  {'created' if snew else 'updated'} — {surl}")
                except Exception as e:
                    say(f"  10b Start here  SKIPPED — {str(e)[:100]}")
            if dest:
                C.mirror_to_drive(st["slug"])
    except Exception as e:
        say(f"  10  Doc         SKIPPED — {str(e)[:140]}")
        say("      the brief is still on disk and on the Drive as HTML")

    # 11. Keep the repo's text mirror current. A record written only when
    # someone remembers to write it is a record nobody trusts; this costs
    # milliseconds and makes the brief greppable and diffable from the repo.
    try:
        import records as _rec
        _rec.main()
    except Exception as e:
        say(f"  11  Records     SKIPPED — {str(e)[:120]}")

    # The copy pack alongside it: her caption and the comments the post drew,
    # so ad copy can be written the moment the creator delivers rather than
    # starting from the finished cut (Damon, 2026-08-27).
    try:
        import copy_source as _cs
        _cs.build()
    except Exception as e:
        say(f"  11  Copy source SKIPPED — {str(e)[:120]}")

    # The framework bank: every swipe's doctrine read on one shelf, so the
    # framework behind a video outlives the brief it was torn down for
    # (Damon's ruling 2026-09-18). It only compiles what stage 1c already
    # filed, so it never raises and never costs a run anything.
    try:
        import framework_bank as _fb
        note = _fb.refresh()
        if note:
            say(f"  12  Bank        {note}")
    except Exception as e:
        say(f"  12  Bank        SKIPPED — {str(e)[:120]}")

    file_to_repo(d)

    say(f"✔ {st['label']} — through to the end")
    return True


VIDEO_EXT = (".mp4", ".mov", ".m4v", ".webm")


def drive_id(video: Path):
    """Google Drive stores each synced file's id in an extended attribute, so a
    file on the mounted Drive can name itself without a lookup."""
    try:
        out = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S",
                              str(video)], capture_output=True, text=True)
        v = out.stdout.strip()
        return v if out.returncode == 0 and len(v) > 10 else ""
    except Exception:
        return ""


def source_url(video: Path):
    """The link that goes at the top of the brief.

    The Drive copy wins (Damon, 2026-08-21). A brief goes out days or weeks
    after the swipe, once the learnings are in it — by then the original post
    may be deleted, gone private, or edited, and a creator opening a dead link
    has nothing to work from. The Drive copy is the version the teardown was
    actually made from, so it is also the honest reference.

    The original post URL is kept as a fallback and recorded either way, so the
    provenance never disappears. If neither exists the line is left out —
    never invented.
    """
    fid = drive_id(video)
    if fid:
        return f"https://drive.google.com/file/d/{fid}/view"
    post = video.parent / "post.json"
    if post.exists():
        try:
            d = json.loads(post.read_text())
            if d.get("url"):
                return d["url"]
        except Exception:
            pass
    return ""


def origin_url(video: Path):
    """Where it came from originally — kept in the record, not in the brief."""
    for name in ("post.json", "meta.json"):     # meta.json: the saves library
        post = video.parent / name
        if post.exists():
            try:
                u = json.loads(post.read_text()).get("url", "")
                if u:
                    return u
            except Exception:
                pass
    return ""


def library_home(video: Path, label: str, st: dict):
    """Where this video's records live on the Drive.

    A video already in the library keeps its own folder. A swipe from somewhere
    else gets one under swipe/, so every asset we tear down ends up in the same
    shape and nothing lives only in a run folder.
    """
    v = video.resolve()
    if "creators" in v.parts and "posts" in v.parts:
        return v.parent
    return L.root() / "swipes" / L.slug(label)


def from_library(video: Path):
    """A video sitting in the library already knows what it is: whose post it
    was, and which post. Read it off the path instead of asking."""
    parts = video.resolve().parts
    creator = label = None
    if "creators" in parts:
        i = parts.index("creators")
        if i + 1 < len(parts):
            creator = parts[i + 1]
        # …/posts/03-DbThHrJIapp/video.mp4
        if "posts" in parts:
            j = parts.index("posts")
            if j + 1 < len(parts):
                label = f"{creator}-{parts[j+1]}"
    return creator, label


def walk_source(folder: Path):
    """Every video under a folder, in order. Points at a Drive folder as easily
    as a local one — the Drive is just a path on this machine."""
    folder = Path(folder).expanduser()
    if not folder.exists():
        sys.exit(f"no such folder: {folder}")
    out = []
    for f in sorted(folder.rglob("*")):
        if f.suffix.lower() in VIDEO_EXT and not f.name.startswith("."):
            out.append(f)
    return out


def already_done(label):
    # The same id `open_run()` would use — asking under the bare slug would
    # tell a second user that Damon's run of this video is theirs, and skip it.
    f = RUNS / C.run_slug(slug(label)) / "run.json"
    if not f.exists():
        return False
    try:
        st = json.loads(f.read_text())
    except Exception:
        return False
    keys = [k for k, v in st.get("stages", {}).items() if v.get("status") == "done"]
    return "stage7" in keys


def main():
    ap = argparse.ArgumentParser(description="Run swiped videos through the chain.")
    ap.add_argument("video", nargs="*")
    ap.add_argument("--queue", action="store_true")
    ap.add_argument("--source", help="a folder of videos — local or on the Drive. "
                    "Every video under it runs, one after another.")
    ap.add_argument("--again", action="store_true",
                    help="with --source, re-run videos that already finished")
    ap.add_argument("--label")
    ap.add_argument("--brand", required=True,
                    help="which brand this run is for. Named every time — a default here would quietly hand one brand's files to another (rule 4).")
    ap.add_argument("--use-identities", action="store_true",
                    help="hand the trained LoRA identities to the frames "
                         "stage. PARKED by default (Damon, 2026-09-02): "
                         "edit-first carries the person from the source "
                         "frame, and a LoRA trained on photoreal images "
                         "fights any style conversion. The lora.json records "
                         "stay on disk; this flag is how they come back.")
    ap.add_argument("--cast", help="which AI cast member fronts the frames when "
                    "several serve the run's avatar (the ai-cast/<name> folder). "
                    "Without it the character who EMBODIES the avatar is cast.")
    ap.add_argument("--product", help="which of the brand's products this run sells, "
                    "when the brand has more than one (the products/<slug>/ folder name). "
                    "With one product it resolves itself; with several the run stops and "
                    "asks rather than guessing.")
    ap.add_argument("--for-avatar", help="declare who this run is for before it starts "
                    "(the core-avatars/<key> folder name). Stage 1b then writes for this "
                    "person instead of choosing one. Use with --for-sub.")
    ap.add_argument("--for-sub", help="the declared sub-avatar (the sub-avatars/<key>.md "
                    "file stem). A video pulled from a sub-avatar's own organic feed "
                    "already knows who it is for.")
    ap.add_argument("--for-awareness", help="declare the awareness level our version ENTERS at "
                    "(a level key from the doctrine's awareness slice, e.g. unaware). A post "
                    "from a feed's entertainment lane enters unaware. Needs --for-avatar.")
    ap.add_argument("--creator", help="their handle, when the video is their own post. "
                    "Without it the run is treated as swipe research: the brief is "
                    "written unassigned and no frames are made.")
    ap.add_argument("--route", choices=["founder", "creator", "ai"],
                    help="how this one gets produced — picks the stage-5 brief. "
                         "Default: creator, the original content-creator brief. "
                         "ai gets the generation brief; founder uses the creator "
                         "brief until a founder brief is cut.")
    ap.add_argument("--only")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="stop")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--video-count", default="3",
                    help="how many videos this creator owes — the creator lane only; "
                         "the general teardown brief no longer takes it")
    ap.add_argument("--no-frames", action="store_true",
                    help="stop after the brief and skip stage 6.")
    ap.add_argument("--board", action="store_true")
    ap.add_argument("--stages", action="store_true", help="show the chain and exit")
    ap.add_argument("--dry-run", "--dry", dest="dry", action="store_true",
                    help="resolve the whole plan and spend nothing: per stage, the "
                         "prompt file and version, every variable OK/MISSING with "
                         "where it comes from, and anything the prompt asks for "
                         "that nothing supplies. No model is called, no run folder "
                         "is opened. Exits non-zero when anything is missing.")
    a = ap.parse_args()

    if a.stages:
        C.report(); return
    if a.board:
        rebuild_board(); return

    if not a.dry:
        stay_awake()
    # The brand names itself. It used to be a literal in the shared
    # config ("=<brand>"), which every brand's run then inherited.
    extras = {"video_count": a.video_count,
              "brand_name": a.brand.replace("-", " ").title(),
              "product": a.product or "",
              # Declared upstream or not at all — the slot is always filled, so
              # the prompt never sees a bare placeholder.
              "declared_avatar": a.for_avatar or "",
              "declared_sub": a.for_sub or "",
              "declared_audience": (
                  f"\nDECLARED AVATAR: {a.for_avatar}\nDECLARED SUB-AVATAR: {a.for_sub or 'none'}\n"
                  "DECLARED BECAUSE: the video was found in this person's own organic feed"
                  + (f"\nDECLARED AWARENESS: {a.for_awareness}" if a.for_awareness else "")
                  if a.for_avatar else "NONE"),
              "declared_awareness": (a.for_awareness or "") if a.for_avatar else ""}

    vids = [Path(v) for v in a.video]
    if a.source:
        found = walk_source(a.source)
        say(f"{len(found)} videos under {a.source}")
        vids += found
    if a.queue:
        QUEUE.mkdir(exist_ok=True)
        vids += sorted(p for p in QUEUE.iterdir()
                       if p.suffix.lower() in (".mp4", ".mov", ".m4v", ".webm"))
    if not vids:
        sys.exit("give me a video, or drop files in queue/ and use --queue")

    only = [x.strip() for x in a.only.split(",")] if a.only else None
    if a.dry:
        # The dry run (2026-09-20): everything below this block is what spends
        # and writes. This block does neither — see dryrun.py.
        import dryrun as _dry
        bad = 0
        for v in vids:
            lib_creator, lib_label = from_library(v)
            label = a.label if len(vids) == 1 and a.label else (lib_label or v.stem)
            res = _dry.resolve(v, label, a.brand, extras=extras, route=a.route,
                               creator=a.creator or lib_creator, only=only,
                               start=a.start, stop=a.stop,
                               want_frames=not a.no_frames, product=a.product)
            bad += _dry.show(res, a.brand, say)
        sys.exit(1 if bad else 0)
    done = skipped = 0
    for v in vids:
        lib_creator, lib_label = from_library(v)
        label = a.label if len(vids) == 1 and a.label else (lib_label or v.stem)
        creator = a.creator or lib_creator
        if a.source and not a.again and already_done(label):
            skipped += 1
            continue
        ok = run_video(v, label, a.brand, only=only, start=a.start, stop=a.stop,
                       redo=a.redo, extras=extras, creator=creator,
                       want_frames=not a.no_frames, route=a.route, cast=a.cast,
                       product=a.product,
                       use_identities=a.use_identities)
        done += 1 if ok else 0
    failed = len([v for v in vids]) - done - skipped
    if a.source or len(vids) > 1:
        say(f"\n{done} finished, {skipped} left alone, {failed} STOPPED SHORT")
    if failed:
        sys.exit(1)
    rebuild_board()


if __name__ == "__main__":
    main()
