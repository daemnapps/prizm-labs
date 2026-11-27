"""Video writing v2 — built beside v1 (2026-10-18). v1 stays the default.

The writing in five calls, two of them merged passes:

  3  Injection                      (runs on the machine, never waits for a session hand)
  A  Reading + Hooks                one call   -> stages/4a-reading.md, 4b-hooks.md
  B  Placement + Expansion + Close  one call   -> stages/4c-placement.md, 4d-expansion.md, 4e-close.md
     Audit                          alone, Opus; a RE-RUN verdict really re-runs the pass it names
  4g Spice
  5  Brief

Every call runs with the prompt cache off (DISABLE_PROMPT_CACHING=1 — the 1-hour
cache write was never read back), gets its inputs cut to what is its own (the offer
bank cut to this product, delivery dials cut to the picked options, each language
section only where it is owned), and logs its real cost and seconds on run.json.
Cost is never a reason to give a pass less to read (VIDEO-RULINGS V17, 2026-10-20):
the teardown's places, props and shot table and the avatar's culture map reach every
pass again (the 2026-10-18 cost trims "tear" and "cmap" are undone, 2026-10-21).

Every pass also gets three inputs of the 2026-10-21 sync: {ask_lane} (the run's paid or
organic lane — it changes only the ask, V1), {video_spice} (the seven layers, V9) and
{realism_index} (the realism index's writing-stage rows, this format's first). The same three reach
the creator and founder route's v1 prompts (verify row 10, 2026-10-21): the teardown fills them through
run_inputs() below, so every route writes on the same lane, spice and realism rules (V1, V9).

The merged passes are split back into v1's stage files and records, so the
board, production and every later reader see exactly what v1 leaves behind.

Prompts: components/video-writing/prompts/v2/ (not a v1 prompt home, so v1
never picks them up).

Run:  python3 components/video-writing/machine/run.py <teardown run> [--allow-new-format]
  or: python3 writing_v2.py <run dir> [--allow-new-format]
  or: video-teardown run.py ... --writing v2   (the teardown hands its writing stages to this file)
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import writing_result as state
import owner_controls
# The chain engine (prompt filling, model calls, the run record) is the teardown's and is
# shared; writing reads it from there by path (video-writing CLAUDE.md, "What it leans on").
TD = HERE.parents[1] / "video-teardown" / "machine"
sys.path.insert(0, str(TD))
import chain as C   # noqa: E402

V2 = C.WRITING_PROMPTS / "v2"
WS = C.WS

# (pass key, display id, file id, name, prompt, [(marker, v1 key, v1 file id, v1 name)])
PASSES = [
    ("stage3", "3", "3", "Injection", "stage3-injection-v11-owner.md", None),
    ("stage4i", "4i", "4i", "Controlling Idea", "stage4i-idea-v3-owner.md", None),   # v3 (2026-11-19, owner approved): the angle chosen first, the concept named · V56: one idea, chosen before the middle is written
    # v11 (2026-11-19): each opening a different customer angle
    ("stage4v2a", "4ab", "4ab", "Reading Hooks", "stage4v2a-readhooks-v11-owner.md",
     [("READING", "stage4r", "4a", "Reading"), ("HOOKS", "stage4b", "4b", "Hooks")]),
    # v11 (2026-11-19): what the lead and the body are for
    ("stage4v2b", "4cde", "4cde", "Placement Expansion Close", "stage4v2b-build-v11-owner.md",
     [("PLACEMENT", "stage4a", "4c", "Placement"), ("EXPANSION", "stage4c", "4d", "Expansion"),
      ("CLOSE", "stage4d", "4e", "Close")]),
    ("stage4e", "4f", "4f", "Audit", "stage4e-audit-v13-owner.md", None),   # v13 (2026-11-19): the native note, no new fail ·   # v5: verify row 11, no NO ENTRY in the rung map
    ("stage4g", "4g", "4g", "Spice", "stage4g-spice-v11-owner.md", None),   # v11 (2026-11-19): organic feel, sale in the back half ·   # v4: V23, organic closes on the turn + the ask
    # the brief as a shooting script (2026-10-21, video-system sync W1-W25): shots, per-line reads, the lane
    # (v4, verify row 22: its history no longer says a scene carries voice_settings)
    ("stage5", "5", "5", "Brief", "stage5-ai-brief-v17-owner.md", None),   # v17 stays live: the swipe's picture and motion are the base (owner, 2026-11-20); v18 (staged fresh) runs only on visuals_ours.json lane brief: true · v17 (2026-11-19): the idea and concept carried by name ·   # v16 (2026-11-18): the style decides the product route · v15 (2026-11-16, V57): v13 + the swipe as backbone; frames drawn by default   # v9 (2026-10-28): brand-free, no rule changed · v8 (2026-10-28): the demo stays on its object; props make sense   # v5: V23, the organic end card is the ask only
]
# the run-time inputs every pass may ask for, filled by run_writing (never from the config)
RUN_INPUTS = ("declared_layers", "ask_lane", "video_spice", "realism_index", "creative_controls", "emotion_video_lines",
              "controls_target", "creative_moves", "owner_notes", "winner_lane", "product_route",
              # what the later stations hand back to the writing (logic layer W1, 2026-11-18); a prompt that asks
              # for none of them gets none of them, so every live prompt reads exactly what it read before
              "winners_feed", "edit_lessons", "winner_breakdown",
              "decision_trail")   # the run's decision trail (W0, run-kit trail.py), NONE when empty
V1_WRITING = ("stage3", "stage4r", "stage4m", "stage4b", "stage4a", "stage4c", "stage4d",
              "stage4e", "stage4g", "stage5")
# what the audit may name, -> the pass that re-runs
RERUN = {"INJECTION": "stage3", "IDEA": "stage4i", "HOOKS": "stage4v2a", "BUILD": "stage4v2b",
         "3": "stage3", "4A": "stage4v2a", "4B": "stage4v2a", "4C": "stage4v2b",
         "4D": "stage4v2b", "4E": "stage4v2b"}
MAX_AUDIT_ROUNDS = 2
STAGE5_STAGED_FRESH = "stage5-ai-brief-v18-owner.md"   # staged fresh from our script (visuals_ours.json lane brief)

CALLS = []          # every paid call this process made: {stage, model, cost_usd, seconds, ...}


# ------------------------------------------------------------------ trimming

def _sections(text, pat):
    idx = [m.start() for m in re.finditer(pat, text)] + [len(text)]
    return text[:idx[0]], [text[a:b] for a, b in zip(idx, idx[1:])]


def offer_slim(offer, product, all_ids):
    """This product's own offers + the guarantee and the hard rules."""
    if not product:
        return offer
    others = set(t for i in all_ids if i != product for t in i.split("-"))
    own = [t for t in product.split("-") if t not in others and len(t) > 2] or [product]
    head, parts = _sections(offer, r"(?m)^##+ ")
    keep = []
    for p in parts:
        h = p.splitlines()[0].lower()
        hid = h.lstrip("# ").split(" ")[0]
        if hid == product or any(t in hid for t in own) or \
                re.match(r"#+ (guarantee|never-pair|brand-owned-claims|rules)\b", h):
            keep.append(p)
    return head + "".join(keep) + "\n(Offer bank cut to this product's own offers, the guarantee and the standing rules.)\n"


def deliv_slim(deliv, doctrine):
    ids = set(re.findall(r"`([a-z0-9 -]+)`", doctrine)) | set(re.findall(r"\b([a-z]+(?:-[a-z]+)+)\b", doctrine)) \
        | set(re.findall(r"\b([a-z]+)\b", doctrine))
    keep = [p for p in _sections(deliv, r"(?m)^### ")[1]
            if (m := re.match(r"### `([^`]+)`", p)) and m.group(1) in ids]
    intros = re.sub(r"(?ms)^### `[^`]+`.*?(?=^##|\Z)", "", deliv)
    return intros + "\n\n(Options shown: only the ones this video's doctrine read picked.)\n\n" + "".join(keep)


def punct_only(spoken):
    i = spoken.find("## 4. The voice-model punctuation map")
    j = spoken.find("\n## ", i + 5)
    return spoken if i < 0 else spoken[i:j if j > 0 else None]


def cut_section(P, start):
    i = P.find(start)
    j = P.find("\n# ", i + 5)
    return P if i < 0 or j < 0 else P[:i] + P[j + 1:]


def angles_compact(raw, avatar):
    try:
        j = json.loads(raw)
    except ValueError:
        return raw
    rows = j.get("angles") if isinstance(j, dict) else j
    if not isinstance(rows, list):
        return raw
    out = [f"- `{a.get('id')}` — {a.get('name')}: {a.get('what')}" for a in rows
           if isinstance(a, dict) and (not avatar or a.get("avatar") in (None, "", avatar))
           and a.get("status", "active") == "active"]
    return "\n".join(out) + "\n" if out else raw


# which cuts each pass gets: only what is not that pass's own (another product's offers, dial options the
# doctrine did not pick, a language section another pass owns). The 2026-10-18 cost trims of the teardown's
# places/props/shot table ("tear") and the culture map ("cmap") are undone (V17, video-system sync W9/W10).
# The build pass's "spice" cut is KEPT on purpose (checked 2026-10-27 against VIDEO-RULINGS V9 (video spice),
# V17 (cost never a reason) and V47 (creative controls)): it is not a cost trim — the spice language belongs to the
# hooks pass (4ab, which writes the openings and keeps it) and to the spice pass (4g, which spices the finished
# script); 4cde builds the middle and the close from the hooks it is handed.
TRIMS = {
    "stage3": ("offer",),
    # an idea prompt that asks for the brand's angle list gets it cut the way the brief does (this avatar's active
    # angles, one line each); the live idea prompt asks for none, so nothing changes for it (2026-11-18)
    "stage4i": ("angles",),
    "stage4v2a": (),
    "stage4v2b": ("offer", "spice", "hooks"),
    "stage4e": ("offer",),
    "stage4g": ("deliv", "depth", "punct"),
    "stage5": ("offer", "deliv", "spoken", "angles"),
}


def _read(p):
    try:
        return Path(p).read_text()
    except OSError:
        return ""


def slim(P, key, d, st):
    """Trim one filled prompt. Each cut replaces an exact source text, so a block
    that is not in this prompt is simply left alone. Returns (prompt, log)."""
    brand, log = st.get("brand", ""), []
    av = (st.get("audience") or {}).get("_avatar") or (st.get("declared_audience") or {}).get("avatar") or ""
    src = {
        "hooks": _read(d / ((st.get("stages") or {}).get("stage4v2a") or {}).get("out", "-")) if key == "stage4v2b" else "",
        "offer": _read(WS / f"brands/{brand}/products/offer-bank.md"),
        "deliv": _read(WS / "components/marketing-doctrine/slices/delivery.md"),
        "spoken": _read(WS / "components/marketing-doctrine/slices/spoken.md"),
        "angles": _read(WS / f"brands/{brand}/strategy/angles.json").strip(),
    }
    ids = re.findall(r"(?m)^## ([a-z0-9-]+) — ", src["offer"])
    doctrine = _read(d / "stages/1c-doctrine.md")
    for t in TRIMS.get(key, ()):
        before = len(P)
        if t == "hooks" and src["hooks"] and src["hooks"] in P:
            P = P.replace(src["hooks"], hooks_for_build(src["hooks"]))
        elif t == "offer" and src["offer"] and src["offer"] in P:
            P = P.replace(src["offer"], offer_slim(src["offer"], st.get("product"), ids))
        elif t == "deliv" and src["deliv"] and src["deliv"] in P:
            P = P.replace(src["deliv"], deliv_slim(src["deliv"], doctrine))
        elif t == "spoken" and src["spoken"] and src["spoken"] in P:
            P = P.replace(src["spoken"], punct_only(src["spoken"]))
        elif t == "angles" and src["angles"] and src["angles"] in P:
            P = P.replace(src["angles"], angles_compact(src["angles"], av))
        elif t == "depth":
            P = cut_section(P, "# Language for this stage — depth")
        elif t == "spice":
            P = cut_section(P, "# Language for this stage — spice")
        elif t == "punct":
            i = P.find("## 4. The voice-model punctuation map")
            j = P.find("\n## ", i + 5)
            if i > 0 and j > 0:
                P = P[:i] + P[j + 1:]
        if len(P) != before:
            log.append((t, before - len(P)))
    return P, log


# ------------------------------------------------------------------ the call

def prior_language_block(d, current_prompt, current_text=""):
    """Carry exact rendered source rows from this run's earlier saved prompts."""
    pattern = (r'(?ms)^- \[(?:language_[^\]\r\n]+|x-[^\]\r\n]+)\] "'
               r'.*?"\r?\n  _[^\r\n]*_(?=\r?\n|\Z)')
    seen = set(re.findall(pattern, current_text))
    sections = []
    for path in sorted((Path(d) / "prompts").glob("*.md")):
        if path.name == Path(current_prompt).name:
            continue
        rows = []
        for row in re.findall(pattern, _read(path)):
            if row not in seen:
                seen.add(row)
                rows.append(row)
        if rows:
            sections.append(f"Source prompt `prompts/{path.name}`\n\n" + "\n\n".join(rows))
    if not sections:
        return ""
    return ("## Prior verbatim language evidence\n\n"
            "Exact source rows supplied in this run's previous saved prompts.\n\n"
            + "\n\n".join(sections) + "\n\n")


def _env():
    import run as R
    e = R._clean_env()
    e["DISABLE_PROMPT_CACHING"] = "1"      # measured 2026-10-18: same prompt $0.84 -> $0.52
    return e


class SessionHandRequired(RuntimeError):
    """Writing needs a session answer, not another provider retry."""
    retryable = False


class HandPromptMismatch(SessionHandRequired):
    """A named session answer was supplied without its matching prompt."""
    retryable = False


def hold_hand_request(run_dir, answer, prompt_bytes, reason):
    """Keep the rejected pair intact and publish a complete new request for the writer."""
    digest = hashlib.sha256(prompt_bytes).hexdigest()[:12]
    current = answer.with_name(f"{answer.stem}.request-{digest}.prompt.md")
    location = os.path.relpath(current, run_dir)
    # A hard link publishes the completed file atomically, without replacing an earlier request.
    try:
        with tempfile.NamedTemporaryFile(dir=answer.parent) as draft:
            draft.write(prompt_bytes)
            draft.flush()
            try:
                os.link(draft.name, current)
            except FileExistsError:
                if not current.is_file() or current.is_symlink() or current.read_bytes() != prompt_bytes:
                    raise HandPromptMismatch(f"session hand held: request file collision at {location}")
    except OSError as exc:
        raise HandPromptMismatch(f"session hand held: could not save current request at {location}: {exc.strerror}") from exc
    raise HandPromptMismatch(f"session hand held: {reason}. Write a new answer from {location}")


def claude_v2(prompt_text, out, model_name=None):
    """v1's claude() with the cache off, the inputs trimmed, and the cost logged.
    Writes on the machine; only when that login is at its limit does it fall to the session hand (19 Oct)."""
    import run as R
    d = out.parent.parent
    st = json.loads((d / "run.json").read_text())
    key = _CURRENT.get("key") or ""
    prompt_text, trims = slim(prompt_text, key, d, st)
    prompt_text = prior_language_block(d, out.name, prompt_text) + prompt_text
    prompt_text = who_block(d, st, out.name) + prompt_text   # WHO IT IS FOR AND WHAT IT MUST SAY (2026-11-25): under the ask and the owner's own words
    prompt_text = owner_block(d, st) + prompt_text       # THE OWNER'S LOCKED SCRIPT (2026-10-23), when the run has one
    prompt_text = story_block(d, st) + prompt_text       # OUR STORY on the swipe's format (2026-10-28), when it has one
    prompt_text = preset_block(d, st) + prompt_text      # THE STORY PRESET (2026-11-21), when the run names one
    prompt_text = ask_block(d) + prompt_text             # THIS AD'S ASK: its offer and moment (2026-11-03), when it has one
    prompt_text = owner_controls.block(d) + prompt_text
    prompt_text = learned_block(d, st) + prompt_text     # WHAT EARLIER RUNS TAUGHT (2026-11-27), on top of every pass
    prompt_bytes = prompt_text.encode("utf-8")
    sent = d / "prompts" / out.name
    if _DRY[0]:                                          # dry: the prompt is filed exactly as it would be sent, no call
        sent.parent.mkdir(parents=True, exist_ok=True)
        sent.write_bytes(prompt_bytes)
        raise DryRunStop(f"dry run: {out.name} prompt filed at prompts/{out.name}, no model called")
    hand = _HAND[0]
    answer = Path(hand) / out.name if hand else None
    if answer and answer.is_file():
        companion = answer.with_suffix(".prompt.md")
        if not companion.is_file():
            hold_hand_request(d, answer, prompt_bytes, f"missing companion prompt {companion.name}")
        if companion.read_bytes() != prompt_bytes:
            hold_hand_request(d, answer, prompt_bytes, f"{companion.name} differs from the current request")
        body = answer.read_bytes()
        if sent.parent.is_dir():
            sent.write_bytes(prompt_bytes)
        out.write_bytes(body)
        song_guard(key, d, out)
        director_after(key, d, out)
        piece_keys(key, d, out)
        return "session-hand"
    if sent.parent.is_dir():
        sent.write_bytes(prompt_bytes)
    model = R._cli_model(model_name or "opus")
    limit = int(os.environ.get("VT_CLAUDE_TIMEOUT", "1500"))
    kit = next(str(p / "components" / "run-kit") for p in Path(__file__).resolve().parents
               if (p / "components" / "run-kit").is_dir())
    if kit not in sys.path:
        sys.path.append(kit)   # appended, never ahead of this machine
    from run_kit.claude_flags import effort_args   # LD-73 (explicit effort)
    t0 = time.time()
    for attempt in (1, 2):
        try:
            # NO ACCOUNT IS WIRED IN (owner, 2026-10-23): started through run_kit's
            # claude_door by the teardown's own _claude_run, cache-off env riding along.
            r = R._claude_run(["--model", model, "--output-format", "json",
                               "--allowed-tools", "", "--append-system-prompt", R.PURE_TEXT],
                              prompt_text, timeout=limit, cwd=str(C.MACHINE), env=_env())
            break
        except subprocess.TimeoutExpired:
            if attempt == 2:
                raise RuntimeError(f"the writer stalled twice ({limit // 60} min each) — stopped rather than left waiting")
    secs = round(time.time() - t0, 1)
    try:
        j = json.loads(r.stdout)
    except ValueError:
        j = None
    said = ((j or {}).get("result") or "") + (r.stderr or "") + (r.stdout or "") if (j is None or j.get("is_error")) else ""
    if hand and any(w in said.lower() for w in ("weekly limit", "usage limit", "rate limit", "session expired", "oauth")):
        # the machine's login is out: any account can carry on — a Claude session writes this stage (same as v1's hand)
        hd = Path(hand); hd.mkdir(parents=True, exist_ok=True)
        (hd / (out.stem + ".prompt.md")).write_bytes(prompt_bytes)
        raise SessionHandRequired(f"waiting for the session hand: {hd / (out.stem + '.prompt.md')}")
    if j is None:
        raise RuntimeError((r.stderr or r.stdout or "claude failed")[-1200:])
    u = j.get("usage") or {}
    rec = dict(stage=key, model=model, cost_usd=round(j.get("total_cost_usd") or 0, 4), seconds=secs,
               api_seconds=round((j.get("duration_api_ms") or 0) / 1000, 1),
               input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"),
               cache_write_tokens=u.get("cache_creation_input_tokens"),
               cache_read_tokens=u.get("cache_read_input_tokens"),
               chars_in=len(prompt_text), trimmed=trims, at=R.now())
    CALLS.append(rec)
    _CURRENT.setdefault("calls", []).append(rec)
    body = j.get("result") or ""
    if j.get("is_error") or not body.strip():
        raise RuntimeError(("claude failed: " + body)[-1200:])
    head = body[:400].lower()
    if sum(w in head for w in R.CHATTER) >= 2:
        raise RuntimeError("the model reported back instead of producing the document — starts: "
                           + body[:180].replace("\n", " "))
    out.write_text(body)
    song_guard(key, d, out)
    director_after(key, d, out)
    piece_keys(key, d, out)
    return model


claude_v2.saves_final_prompt = True


# ---------- stage 5d: the director, on the brief stage 5 just wrote ----------

def song_guard(key, d, out):
    """THE SWIPE'S SONG IS NEVER OURS (2026-11-20). Stage 5 copied a swipe's recorded song (its lyrics, no style row)
    into the brief as a sung piece; production refused it and the lyrics are someone else's. A song block whose style
    is unfilled, or whose lines are the swipe's own words, becomes an instrumental bed in the swipe's feel (production
    makes it on ElevenLabs Music, the ruled door): sections emptied, the swipe's measured sound written as `bed`."""
    if key != "stage5":
        return None
    try:
        text = Path(out).read_text()
    except OSError:
        return None
    blocks = list(re.finditer(r"```json\n(.*?)\n```", text, re.S))
    if not blocks:
        return None
    m = blocks[-1]
    try:
        doc = json.loads(m.group(1))
    except ValueError:
        return None
    song = doc.get("song") if isinstance(doc, dict) else None
    if not isinstance(song, dict) or not song.get("sections"):
        return None
    lines = [str(l).strip().lower() for sec in song["sections"] for l in (sec.get("lines") or []) if str(l).strip()]
    try:
        heard = (Path(d) / "stages" / "1-transcript.md").read_text().lower()
    except OSError:
        heard = ""
    swiped = [l for l in lines if len(l) > 8 and l.rstrip(".!?,") in heard]
    unfilled = str(song.get("style_id") or "").strip() in ("", "[UNFILLED]")
    if not (unfilled or swiped):
        return None
    try:
        feel = json.loads((Path(d) / "music" / "music.json").read_text()).get("described") or ""
    except (OSError, ValueError):
        feel = ""
    doc["song"] = {"style_id": None, "vocal": None, "bpm": song.get("bpm"), "sections": [],
                   "bed": "instrumental in the swipe's feel, made on ElevenLabs Music: " + feel[:400],
                   "why": ("the lines are the swipe's own song" if swiped else "no style row was chosen")
                          + " (song guard 2026-11-20)"}
    Path(out).write_text(text[:m.start(1)] + json.dumps(doc, indent=1, ensure_ascii=False) + text[m.end(1):])
    import run as R
    R.say(f"      song: the swipe's song is not ours — {len(swiped)} copied line(s); the brief carries an instrumental bed")
    return doc["song"]


def director_after(key, d, out, caller=None):
    """Stage 5d runs the moment stage 5's brief lands, before any stage-5 check reads it (the owner, 2026-11-17:
    creativity on the chain, the machine keeps one idea per scene). Every check after it, and the acceptance stamp,
    read the directed brief. machine/director.py does the work; a director that cannot run stops the stage (2026-11-20:
    an undirected scene is a swipe copy, never ours). Only the stage-5 brief itself, never a patch."""
    if key != "stage5":
        return None
    try:
        text = Path(out).read_text()
    except OSError:
        return None
    if "```json" not in text or '"scenes"' not in text:
        return None                                       # no scene block (the creator route): nothing to direct
    import run as R
    import importlib.util
    sp = importlib.util.spec_from_file_location("vw_director", HERE / "director.py")
    D = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(D)
    try:
        picks = D.direct(d, caller=caller or director_call, brief=out, ws=WS)
        kept = sum(1 for p in picks.values() if p.get("kept"))
        rec = {"station": D.STATION, "state": "done", "kept": kept, "scenes": len(picks),
               "record": "director/picks.json", "at": R.now()}
        R.say(f"  5d  Director    {kept}/{len(picks)} scenes restaged, one idea each → director/picks.md")
    except SystemExit as e:
        rec = {"station": D.STATION, "state": "nothing to direct", "why": str(e)[:200], "at": R.now()}
    except Exception as e:  # noqa: BLE001 — an undirected brief never goes on (owner ruling 2026-11-20: every visual
        # is ours); the stage fails with the reason on the run and is run again
        rec = {"station": D.STATION, "state": "failed", "why": f"{type(e).__name__}: {str(e)[:200]}", "at": R.now()}
        R.say(f"  5d  Director    could not run ({rec['why'][:120]}) — STOP: the brief is not accepted undirected")
        _CURRENT["director"] = rec
        raise
    _CURRENT["director"] = rec
    return rec


def director_call(text, tier):
    """One 5d call on the writing chain's own door (the teardown's _claude_run: this run's credential, a mini run's
    requester kept), on run-kit's tier model, its cost logged with the stage's calls as `stage5d`."""
    import run as R
    kit = str(WS / "components" / "run-kit")
    if kit not in sys.path:
        sys.path.append(kit)   # appended, never ahead of this machine
    from run_kit.model import TIERS
    model = TIERS[tier]
    t0 = time.time()
    r = R._claude_run(["--model", model, "--output-format", "json", "--allowed-tools", "",
                       "--append-system-prompt", R.PURE_TEXT], text,
                      timeout=int(os.environ.get("VT_CLAUDE_TIMEOUT", "1500")), cwd=str(C.MACHINE), env=_env())
    try:
        j = json.loads(r.stdout)
    except ValueError:
        raise RuntimeError((r.stderr or r.stdout or "claude failed")[-600:])
    body = j.get("result") or ""
    if j.get("is_error") or not body.strip():
        raise RuntimeError(("claude failed: " + body)[-600:])
    u = j.get("usage") or {}
    rec = dict(stage="stage5d", model=model, cost_usd=round(j.get("total_cost_usd") or 0, 4),
               seconds=round(time.time() - t0, 1), api_seconds=round((j.get("duration_api_ms") or 0) / 1000, 1),
               input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"), chars_in=len(text), at=R.now())
    CALLS.append(rec)
    _CURRENT.setdefault("calls", []).append(rec)
    return body


# ------------------------------------------------------------------ the owner's locked script (2026-10-23)
# owner, 2026-10-23, after a hand-typed brief broke the pastor barber body: the chain had no door for a script HE wrote
# ("build the door"). The script goes in as a file (--owner-script); every writing pass is handed it as fixed words
# — carry every spoken line verbatim, build everything else (structure, scenes, frames, beats, B-roll, the brief)
# around it — and after the brief the words are checked line by line: a line missing or changed holds the brief,
# named. The script file lives in the run folder (owner-script.md) and run.json records who locked it and its hash.

OWNER_FILE = "owner-script.md"


# ------------------------------------------------------------------ what earlier runs taught (2026-11-27)
# Every correction the owner made on an earlier run is a learning in force (components/run-kit run_kit/learnings.py,
# runs/learnings/): every pass is handed the writing station's rules for this brand and format, the run records which
# (learnings-handed.json), the audit loop sends a draft that breaks one back to the build, and a script he locks over
# the chain's is captured as candidates for the next run.

def _learnings():
    kit = str(WS / "components" / "run-kit")
    if kit not in sys.path:
        sys.path.append(kit)
    from run_kit import learnings as LN
    return LN


def learned_block(d, st):
    try:
        LN = _learnings()
        return LN.handed(d, "writing", st.get("brand"), fmt=st.get("format_id")) if LN.real_run(d) else ""
    except Exception as e:  # noqa: BLE001 -- a store that will not read never stops a pass
        print(f"  learnings not read ({type(e).__name__})")
        return ""


def learned_findings(d, st):
    """Every rule in force the current script breaks, as lines for the build's repair (empty when none or unread)."""
    try:
        LN = _learnings()
        if not LN.real_run(d):
            return []
        keys = ("stage4a", "stage4b", "stage4c", "stage4d")
        text = "\n".join((d / st["stages"][k]["out"]).read_text() for k in keys
                         if (st.get("stages") or {}).get(k, {}).get("out") and (d / st["stages"][k]["out"]).is_file())
        return LN.findings(text, st.get("brand"), ("writing",), st.get("format_id"))
    except Exception:  # noqa: BLE001
        return []


def learned_rerun(d, st, again):
    """The audit's answer, with every learning in force the script breaks added on top: a script the audit would
    ship goes back to the build with them; an audit STOP is never overridden."""
    broken = learned_findings(d, st)
    if not broken:
        return again
    rec = (st.get("stages") or {}).get("stage4e") or {}
    f = d / (rec.get("out") or "stages/4f-audit.md")
    if f.is_file() and re.search(r"VERDICT\W*\s*STOP", f.read_text(), re.I):
        return again
    note = "BREAKS WHAT EARLIER RUNS TAUGHT — fix each before anything else:\n" + "\n".join(broken) + "\n\n"
    return (again[0], note + again[1]) if again else ("stage4v2b", note)


def learned_capture(d, st, kept):
    """The owner's locked script against the chain's own: each changed line a candidate learning."""
    try:
        keys = ("stage4a", "stage4b", "stage4c", "stage4d")
        made = "\n".join((d / st["stages"][k]["out"]).read_text() for k in keys
                         if (st.get("stages") or {}).get(k, {}).get("out") and (d / st["stages"][k]["out"]).is_file())
        if made and _learnings().real_run(d):
            _learnings().capture(st.get("brand"), "writing", made, kept, run=d.name, file=OWNER_FILE)
    except Exception as e:  # noqa: BLE001
        print(f"  learnings not captured ({type(e).__name__})")


def owner_block(d, st):
    rec = st.get("owner_script") or {}
    f = Path(d) / (rec.get("file") or OWNER_FILE)
    if not rec or not f.is_file():
        return ""
    return ("## OWNER'S LOCKED SCRIPT — read this before anything else\n\n"
            f"Locked by {rec.get('by') or 'the owner'} on {rec.get('at', '')[:10]}. The spoken lines below are final and "
            "approved. Carry EVERY spoken line VERBATIM — same words, same order, same speaker — wherever this pass "
            "writes or places lines; never rewrite, trim, add to, reorder or 'improve' one. The creative decisions "
            "written with it (the concept, the set-ups, the B-roll each claim gets, the beats called out) are the plan "
            "this pass builds on. This pass's job is everything AROUND the words: structure, scenes, frames, beats, "
            "delivery, B-roll and the brief. Where this pass's own instructions would change the words, the words win: "
            "say so in one line and keep them.\n\n" + f.read_text().strip() + "\n\n## END OF THE OWNER'S LOCKED SCRIPT\n\n")


def owner_lines(text):
    """The locked spoken lines: every row of the script's LINES table (| scene | speaker | line |)."""
    out, on = [], False
    for ln in text.splitlines():
        if re.match(r"^#+\s*LINES\b", ln.strip(), re.I):
            on = True
            continue
        if on and re.match(r"^#+\s", ln.strip()):
            break
        if on and ln.strip().startswith("|") and not re.match(r"^\|\s*-", ln.strip()):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[2] and cells[2].lower() != "line":
                out.append({"scene": cells[0], "speaker": cells[1], "line": cells[2]})
    return out


def _norm(s):
    s = s.replace("’", "'").replace("…", " ").replace("—", " ").lower()
    return " ".join(re.sub(r"[^a-z0-9' ]", " ", s).split())


def owner_words_check(d, st):
    """Every locked line must be in the brief word for word (punctuation and case aside). Returns the misses."""
    rec = st.get("owner_script") or {}
    f = Path(d) / (rec.get("file") or OWNER_FILE)
    brief = Path(d) / ((st.get("stages") or {}).get("stage5") or {}).get("out", "stages/5-brief.md")
    if not rec or not f.is_file() or not brief.is_file():
        return None
    body = _norm(brief.read_text())
    return [r for r in owner_lines(f.read_text()) if _norm(r["line"]) not in body]


def stock_moment_check(d, st):
    """Say so when a finished script leans on a moment the brand has overused. A swipe's own moment can
    earn it, so this reports and never holds (language-layer experience.py, 2026-11-02)."""
    f = Path(d) / "stages" / "4cde-placement-expansion-close.md"
    if not f.is_file():
        return
    lang = WS / "components" / "language-layer"
    if str(lang) not in sys.path:
        sys.path.append(str(lang))
    from language_layer import experience as X
    hits = X.repeats(f.read_text(), st["brand"])
    if hits:
        print("  stock moments in this script: " + ", ".join(f"{k} ({v})" for k, v in hits.items()))


def apply_owner_check(d):
    """Run the words check and record it; a miss holds the brief. None = the run has no locked script."""
    d = Path(d)
    st = json.loads((d / "run.json").read_text())
    missed = owner_words_check(d, st)
    if missed is None:
        return None
    st["owner_words_check"] = {"passed": not missed, "missing": missed}
    if missed:
        s5 = st.setdefault("stages", {}).setdefault("stage5", {})
        s5["status"] = "held"
        s5["error"] = "the owner's locked words are not all in the brief: " + "; ".join(
            f"{m['scene']} {m['speaker']}: {m['line'][:60]}" for m in missed[:6])
    (d / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    return not missed


# ------------------------------------------------------------------ our own story on the swipe's format (2026-10-28)
# owner, 2026-10-28, on the first song ad through the new chain: "we don't need a teardown just the writing" — the
# swipe gives the format, the structure and the style; the story is OURS (a concept from the research bank). The
# concept goes in as a file (--story); every writing pass is handed it: the swipe's structure, pacing and devices stay,
# its story, people and facts do not. --format names the format the piece is written in (a row of the format bank).

STORY_FILE = "story.md"


def story_block(d, st):
    rec = st.get("story") or {}
    f = Path(d) / (rec.get("file") or STORY_FILE)
    if not rec or not f.is_file():
        return ""
    return ("## OUR STORY — read this before anything else\n\n"
            "This piece tells the story below, not the swipe's. From the swipe keep its FORMAT, STRUCTURE, PACING, "
            "STYLE and DEVICES (how a beat is set up, paid off, shown); drop its story, its people, its facts and its "
            "product. Every beat, person, line, set and prop of the piece comes from this story; where this pass's own "
            "instructions point at the swipe's story, use this one instead and say so in one line. The guards written "
            "in it (what is never named, never claimed, never shown) are hard rules.\n\n"
            + f.read_text().strip() + "\n\n## END OF OUR STORY\n\n")


# ------------------------------------------------------------------ the ask this ad was ordered with (2026-11-03)
# The creative strategist writes an ask per promotion (runs/creative-strategist/<brand>/<ask>/ask.json): the offer
# lines the ad may say, the lines it may never say, and the moment with its window. Image and copy writing already
# read it from the run's vars/ask.md (image-writing tools/writing.py offer_input, copywriter brief_words.py); video
# writing read only the offer bank, so a promo's moment and its offer reached a video only through the end card.
# Same convention here: vars/ask.md holds the ask record's repo-relative path; every pass is handed the ask on top,
# and run.json keeps the moment so later stations read it from the run.

ASK_FILE = "vars/ask.md"


def ask_record(d):
    """(repo-relative path, ask record) named on this run, or (None, None) when it names none.
    A named ask that cannot be read is an error, never a quiet fall back to the bank alone."""
    f = Path(d) / ASK_FILE
    ref = f.read_text().strip() if f.is_file() else ""
    if not ref:
        return None, None
    p = Path(ref) if Path(ref).is_absolute() else WS / ref
    try:
        return ref, json.loads(p.read_text())
    except (OSError, ValueError) as e:
        raise RuntimeError(f"the ask named on this run ({ref}) could not be read: {e}")


def ask_block(d):
    ref, rec = ask_record(d)
    if not rec:
        return ""
    off, mom = rec.get("offer") or {}, rec.get("moment") or {}
    if not isinstance(mom, dict):
        mom = {"key": mom}
    say = "\n".join(f'- "{x}"' for x in off.get("lines") or []) or "- (the ask names no offer lines)"
    never = "\n".join(f"- {x}" for x in off.get("never") or []) or "- (the ask names none)"
    when = "\n".join(f'- "{x}"' for x in mom.get("lines") or [])
    return (f"## THIS AD'S ASK — `{rec.get('ask') or Path(ref).parent.name}` (read this before anything else)\n\n"
            "This ad was ordered for the promotion below. Where these rules differ from the offer bank or anything "
            "else in this prompt, THESE WIN. A line the bank allows but the NEVER list forbids is not used anywhere in "
            "the piece — not spoken, not on screen, not on the end card.\n\n"
            + (f"Funnel: {rec['funnel']}\n\n" if rec.get("funnel") else "")
            + f"### Offer lines this ad may say, word for word\n\n{say}\n\n"
            f"### Never on this ad\n\n{never}\n\n"
            + (f"### The moment: `{mom.get('key', '')}`, {mom.get('window', '')}\n\n"
               + (f"The piece carries one of these, word for word:\n\n{when}\n\n" if when else "")
               if mom.get("key") else "")
            + "The brief names this ask, its moment and window, and the offer lines it uses in its header.\n\n"
            "## END OF THIS AD'S ASK\n\n" + idea_block(rec))


def idea_block(rec):
    """The idea of a research-route ask (creative-strategist `idea.block`), on every pass (2026-11-25); "" when it has none."""
    if not (rec.get("strategy") or {}).get("idea"):
        return ""
    import importlib.util
    spec = importlib.util.spec_from_file_location("creative_strategist_idea", str(WS / "components/creative-strategist/machine/idea.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.block(rec) + "\n"


# ------------------------------------------------------------------ who this ad is for, and what it must say (2026-11-25)
# The one read of the person and the message (creative-strategist who.py) goes on every pass that writes or judges
# words, and on none that reads the swipe. The decisions are the run's own; nothing is decided here.

WRITES_WORDS = re.compile(r"^(3|4[a-z]+|5)-")       # the writing's stage files; the teardown's are 0- to 2-
_WHO = []


def who_module():
    """creative-strategist who.py, loaded once. Its folders end up last on sys.path, never ahead of this machine."""
    if not _WHO:
        import importlib.util
        home = HERE.parents[1] / "creative-strategist" / "machine"
        before = list(sys.path)
        spec = importlib.util.spec_from_file_location("creative_strategist_who", str(home / "who.py"))
        m = importlib.util.module_from_spec(spec)
        try:
            if str(home) not in sys.path:
                sys.path.append(str(home))
            spec.loader.exec_module(m)
        finally:
            sys.path[:] = before + [x for x in dict.fromkeys(sys.path) if x not in before]
        _WHO.append(m)
    return _WHO[0]


def who_args(d, st, out_name=""):
    """(brand, avatar, sub, demographic, what) as this run decided them, or None while it has no avatar."""
    dec, aud, ms = st.get("declared_audience") or {}, st.get("audience") or {}, st.get("market_state") or {}
    brand, avatar = st.get("brand"), dec.get("avatar") or aud.get("_avatar")
    if not brand or not avatar:
        return None
    ordered = (ask_record(d)[1] or {}).get("aim") or {}       # the ask's own decisions, where the run has made none
    level = re.match(r"[a-z-]+", str(ms.get("awareness") or _run_awareness(st) or "").strip().strip("`").lower())
    claim = st.get("claim") or st.get("angle")
    if not claim and not out_name.startswith(("3-", "4i-")):  # the angle 4i chose; never handed back to 4i itself
        m = re.search(r"(?m)^ANGLE:\s*(.+)$", _read(Path(d) / "stages" / "4i-controlling-idea.md"))
        claim = m.group(1).strip() if m and not m.group(1).lower().startswith("none") else None
    if isinstance(claim, dict):
        claim = claim.get("claim") or claim.get("name") or claim.get("id")
    what = {"desire": ms.get("lead_desire"), "awareness": level.group(0) if level else None,
            "stage": ms.get("sophistication"), "leads_with": ms.get("sophistication_leads_with"),
            "doubt": st.get("doubt"), "claim": claim}
    what = {k: v or ordered.get(k) for k, v in what.items()}
    what["creative"] = True
    try:
        what["cell"] = json.loads(_read(Path(d) / "matrix-cell.json") or "{}").get("text")   # its row on the creative matrix
    except ValueError:
        pass
    what["product"] = st.get("product") or None               # the Body Map: a product never written for a place it is ruled out for
    sub = dec.get("sub") or aud.get("_sub_avatar") or None
    return brand, avatar, sub, dec.get("demographic") or (st.get("moves") or {}).get("face") or ordered.get("demographic"), what


def _matrix():
    p = str(Path(__file__).resolve().parents[2] / "creative-diversity")
    if p not in sys.path:
        sys.path.append(p)
    import creative_matrix
    return creative_matrix


def _matrix_off():
    return os.environ.get("QC_DIVERSITY", "1") == "0" or "unittest" in sys.modules


def matrix_start(d, st, ask=None):
    """NO ROW, NO START (owner, 2026-11-26): before anything is written, the run has its row on the creative matrix, fitted to
    its swipe's own format. The reason it may not start, or "" ."""
    if _matrix_off():
        return ""
    try:
        args = who_args(d, st)
        if not args:
            return ""
        fmt = ((st.get("combo") or {}).get("format") or (st.get("moves") or {}).get("format")
               or (st.get("layers") or {}).get("format") or st.get("format_id"))
        MX = _matrix()
        ok = fmt if fmt in MX.values(args[0], "video")["format"] else None
        MX.start(d, args[0], args[2] or args[1], "video", {"format": ok}, ask=ask)
        return ""
    except ValueError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001 -- a reader that cannot run is said, never a lost run
        print("  matrix: not made (%s: %s)" % (type(e).__name__, str(e)[:140]))
        return ""


def matrix_written(d, st, ask=None):
    """What was written against its row: "" when it holds, else what to change. The read failing never stops a run."""
    if _matrix_off():
        return ""
    try:
        MX = _matrix()
        r, args = MX.row_of(d), who_args(d, st)
        if not (r and args):
            return ""
        mv = MX.PL.known(MX.PL.read(args[0], _read(Path(d) / "stages" / "3-injection.md"), ask or MX.ask_model), {"sub": args[2], "avatar": args[1], "awareness": args[4].get("awareness"), "demographic": args[3]})
        n, off = MX.back(r["moves"], mv)
        (Path(d) / "matrix-read.json").write_text(json.dumps({"as_planned": n, "off": off, "moves": mv}, indent=1) + "\n")
        print("  matrix: %d of 7 as its row says" % n)
        return "" if len(off) <= 2 else "It left its row on the creative matrix: " + "; ".join("%s is planned %s, it was written %s" % x for x in off) + ".\nKeep what works and write it inside its row:\n\n" + r["text"]
    except Exception as e:  # noqa: BLE001
        print("  matrix: not read (%s: %s)" % (type(e).__name__, str(e)[:120]))
        return ""


def who_block(d, st, out_name=""):
    """who.block for this run; "" on a pass that reads the swipe, or before the run has an avatar. A sub-avatar that
    does not exist stops with who.py's own message (SystemExit); anything else prints one line and adds nothing."""
    if out_name and not WRITES_WORDS.match(out_name):
        return ""
    try:
        args = who_args(d, st, out_name)
        if not args:
            return ""
        W = who_module()
        W.selection(args[0], args[1], args[2])
        if args[1] not in W.avatars(args[0]):
            print("  who block: no avatar %s under %s, so none is added" % (args[1], args[0]))
            return ""
        return W.block(*args)
    except Exception as e:  # noqa: BLE001 -- the block never costs a run
        print("  who block could not be built (%s: %s)" % (type(e).__name__, str(e)[:120]))
        return ""


def who_attach(d, st):
    """The full profile (person, look, message) saved with the run, so the brief carries all of it (2026-11-25)."""
    args = who_args(d, st)
    return who_module().attach(d, *args) if args else None


def who_stamp(d, st):
    """The same decisions as data, for run.json `aim`; None before an avatar. A missing sub-avatar stops (SystemExit)."""
    try:
        args = who_args(d, st)
        W = who_module() if args else None
        return W.stamp(*args) if W and args[1] in W.avatars(args[0]) else None
    except Exception as e:  # noqa: BLE001
        print("  who stamp could not be made (%s: %s)" % (type(e).__name__, str(e)[:120]))
        return None


def name_ask(d, ask, brand=None):
    """Name the ask on a run: an ask.json path (repo-relative or not), or an ask's name under
    runs/creative-strategist/<brand>/. Writes vars/ask.md and keeps the moment on run.json."""
    d = Path(d)
    st = json.loads((d / "run.json").read_text())
    brand = brand or st.get("brand") or ""
    p = Path(ask)
    cands = [p, WS / p, WS / "runs" / "creative-strategist" / brand / ask / "ask.json"]
    hit = next((c for c in cands if c.is_file()), None)
    if not hit:
        raise SystemExit(f"no ask at {ask} — an ask.json path, or an ask name under "
                         f"runs/creative-strategist/{brand}/")
    hit = hit.resolve()
    try:
        ref = str(hit.relative_to(WS.resolve()))
    except ValueError:
        raise SystemExit(f"{hit}: the ask must live in the workspace (a repo-relative path is what the run keeps)")
    (d / ASK_FILE).parent.mkdir(parents=True, exist_ok=True)
    (d / ASK_FILE).write_text(ref + "\n")
    rec = json.loads(hit.read_text())
    mom = rec.get("moment") or {}
    if not isinstance(mom, dict):
        mom = {"key": mom}
    st["ask"] = {"file": ref, "ask": rec.get("ask") or hit.parent.name,
                 "moment": mom.get("key"), "window": mom.get("window"),
                 "offer_lines": list((rec.get("offer") or {}).get("lines") or [])}
    (d / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    return st


# ------------------------------------------------------------------ the story preset this piece is written in (2026-11-21)
# Owner direction 2026-11-21: formats, then presets of those formats; a preset picked and filled by our chain with our
# research and dials is how any creative is written at volume. A story preset (creative-controls story_presets.json,
# brand-free) fixes the SHAPE: beats at % marks, where the product enters, cast roles, tone, captions, length. Every
# pass is handed it on top; everything inside the shape still comes from the brand's own inputs the prompts already
# bind (avatar, culture map, verbatim language, objection bank, offer bank, dials, house rules). --preset <id> names
# one; --preset auto picks one from the run's format and awareness, skipping presets already written for this avatar.

PRESET_FILE = "vars/story-preset.md"


def _story_presets():
    cc = str(WS / "components" / "creative-controls")
    if cc not in sys.path:
        sys.path.append(cc)   # appended, never ahead of this machine
    import story_presets as SP
    return SP


def _run_avatar(st):
    return ((st.get("declared_audience") or {}).get("avatar") or (st.get("audience") or {}).get("_avatar") or "")


def _run_awareness(st):
    aw = st.get("awareness")
    return (st.get("scratch") or {}).get("awareness") or (aw.get("level") if isinstance(aw, dict) else aw) or None


def presets_used(brand, avatar, skip=None):
    """Story presets already written for this brand's avatar (newest runs' run.json), so auto-pick rotates."""
    root = WS / "runs" / "video-teardown" / "_work"
    used = []
    for f in root.glob("*/run.json") if root.is_dir() else []:
        if skip and f.parent == Path(skip):
            continue
        try:
            st = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        sp = st.get("story_preset") or {}
        if sp.get("id") and st.get("brand") == brand and _run_avatar(st) == avatar:
            used.append(sp["id"])
    return used


def name_preset(d, pid):
    """Name the story preset on a run: an id from the bank, or `auto`. Writes vars/story-preset.md and keeps
    {id, name, picked_by, why} on run.json. An unknown id stops here, before any pass."""
    SP = _story_presets()
    d = Path(d)
    st = json.loads((d / "run.json").read_text())
    if pid == "auto":
        fmt = (st.get("layers") or {}).get("format") or st.get("format_id") or ""
        fmt = fmt if fmt in {(p.get("format") or {}).get("script_format") for p in SP.load()["presets"]} else None
        used = presets_used(st.get("brand"), _run_avatar(st), skip=d)
        ranked = SP.pick(script_format=fmt, awareness=_run_awareness(st), length="short", used=used)
        if not ranked:
            raise SystemExit("no story preset fits format %r — name one with --preset <id>" % fmt)
        p, why = ranked[0]
        rec = {"id": p["id"], "name": p["name"], "picked_by": "chain",
               "why": "format %s, avatar %s: %s" % (fmt or "any", _run_avatar(st) or "none", why)}
    else:
        try:
            p = SP.get(pid)
        except KeyError as e:
            raise SystemExit(str(e).strip('"'))
        rec = {"id": p["id"], "name": p["name"], "picked_by": "named", "why": "named on the run"}
    (d / PRESET_FILE).parent.mkdir(parents=True, exist_ok=True)
    (d / PRESET_FILE).write_text(p["id"] + "\n")
    st["story_preset"] = rec
    (d / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    return rec


def preset_block(d, st):
    """The named story preset, on top of every pass; "" when the run names none."""
    f = Path(d) / PRESET_FILE
    pid = f.read_text().strip() if f.is_file() else ""
    if not pid:
        return ""
    SP = _story_presets()
    try:
        return SP.block(SP.get(pid), seconds=st.get("target_seconds"))   # our length, not the card's (2026-11-21)
    except KeyError:
        raise RuntimeError(f"the story preset named on this run ({pid}) is not in the bank")


def preset_check(d):
    """The code half of the preset's check on the written brief: notes, never a hold (only money and law hold)."""
    d = Path(d)
    f, b = d / PRESET_FILE, d / "stages" / "5-brief.md"
    if not f.is_file() or not b.is_file():
        return None
    blocks = re.findall(r"```json\s*\n(.*?)\n```", b.read_text(), re.S)
    try:
        doc = json.loads(blocks[-1]) if blocks else {}
    except ValueError:
        doc = {}
    SP = _story_presets()
    notes = SP.check_brief(doc, SP.get(f.read_text().strip()))
    st = json.loads((d / "run.json").read_text())
    st.setdefault("writing_notes", {})["story_preset"] = notes
    (d / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    return notes


# a dry run: every input and block is built and the prompt is filed as sent, then the pass stops before the model
_DRY = [False]


class DryRunStop(RuntimeError):
    pass


def writing_keys():
    keys = set(V1_WRITING)
    for key, _sid, _fid, _name, _prompt, splits in PASSES:
        keys.add(key)
        keys.update(row[1] for row in splits or [])
    return keys


def invalidate_written(st, reason):
    """Keep artifacts and retry limits; completed writing must be checked again after an input change."""
    for key in writing_keys():
        rec = (st.get("stages") or {}).get(key) or {}
        if rec.get("status") == "done":
            rec.update(status="stale", stale_because=reason)


def register_pass_order(st, passes):
    """Give the shared engine the real v2 dependencies, including its emitted v1 files."""
    old = st.get("_order") or []
    upstream = ("stage0", "stage1", "stage1k", "stage1c", "stage1b", "stage2")
    ordered = [key for key in upstream if key in old or key in (st.get("stages") or {})]
    for stage in passes:
        ordered.append(stage["key"])
        ordered.extend(row[1] for row in stage.get("splits") or [])
    st["_order"] = list(dict.fromkeys(ordered + list(old)))
    stale = None
    for key in st["_order"]:
        rec = (st.get("stages") or {}).get(key) or {}
        if rec.get("status") == "stale":
            stale = stale or key
        elif stale and key in writing_keys() and rec.get("status") == "done":
            rec.update(status="stale", stale_because=f"{stale} changed upstream writing inputs")


def lock_story(d, src, by="owner"):
    import hashlib
    from datetime import datetime, timezone
    d = Path(d)
    text = Path(src).read_text()
    story = d / STORY_FILE
    changed = not story.is_file() or story.read_text() != text
    story.write_text(text)
    st = json.loads((d / "run.json").read_text())
    if changed:
        invalidate_written(st, "story changed through --story")
    st["story"] = {"file": STORY_FILE, "by": by, "source": str(src),
                   "sha": hashlib.sha256(text.encode()).hexdigest()[:16],
                   "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (d / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    return st


def set_format(d, fid):
    """The piece's format, named outright (a row of the format bank); the swipe's own read stays in its stages."""
    d = Path(d)
    st = json.loads((d / "run.json").read_text())
    st.setdefault("layers", {})
    st["layers"] = dict(st["layers"] or {}, format=fid)
    st["format_id"] = fid
    (d / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    return st


def lock_owner_script(d, src, by="owner"):
    import hashlib
    from datetime import datetime, timezone
    d = Path(d)
    text = Path(src).read_text()
    if not owner_lines(text):
        raise SystemExit(f"{src}: no LINES table (| scene | speaker | line |) — the locked words must be listed line by line")
    (d / OWNER_FILE).write_text(text)
    st = json.loads((d / "run.json").read_text())
    st["owner_script"] = {"file": OWNER_FILE, "by": by, "source": str(src), "lines": len(owner_lines(text)),
                          "sha": hashlib.sha256(text.encode()).hexdigest()[:16],
                          "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (d / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    learned_capture(d, st, text)
    return st


_CURRENT = {}
_HAND = [None]          # the session-hand folder, kept across passes (_CURRENT is cleared each pass)


# ------------------------------------------------------------------ plan

def declared_layers(st):
    """The four layers teardown decided — the writing never re-guesses them."""
    lay = st.get("layers") or {}          # teardown v2's four layers, when it ran
    fid = lay.get("format") or st.get("format_id") or "unknown"
    row = {}
    try:
        lib = json.loads((WS / "components/elements/library/format.video.json").read_text())
        row = next((r for r in lib["rows"] if r["id"] == fid.replace("new:", "")), {})
    except (OSError, ValueError, KeyError):
        pass
    doc = st.get("doctrine") or {}
    # THE REASON BESIDE THE NAME (logic layer W1, 2026-11-18): the triage says why it called each layer what it
    # called it; only the names used to reach the writing. A layer with no reason on file prints as before.
    said = lay.get("_why") if isinstance(lay.get("_why"), dict) else st.get("layer_reasons")   # the older chain's home
    said = said if isinstance(said, dict) else {}

    def why(el):
        return f"\n  - why it was called that: {said[el]}" if said.get(el) else ""
    lines = [f"- **FORMAT:** `{fid}`" + (f" — {row.get('name')}: {row.get('what')}" if row else
                                         (" — a format new to the bank, approved for this run" if fid.startswith("new:") else ""))
             + why("format"),
             f"- **STYLE:** `{lay.get('style') or st.get('style_id') or 'unknown'}`" + why("style"),
             f"- **STRUCTURE:** {lay.get('structure') or doc.get('framework') or 'as the doctrine read gives it'}" + why("structure"),
             f"- **HOW IT'S MADE:** {lay.get('made') or st.get('production_route') or 'creator'}" + why("made")]
    beats = (row.get("extra") or {}).get("beats") if row else None
    if beats:
        lines.append(f"- **THE FORMAT'S BEATS:** {beats}")
    pb, where = format_playbook(fid)
    if pb:
        lines.append(f"- **THE FORMAT'S PLAYBOOK** ({where}) — how this format is made, stage by stage; write "
                     f"inside it, and where the swipe itself differs, the swipe wins:\n\n{pb.strip()}")
    return "\n".join(lines)


PLAYBOOKS = WS / "components/video-production/formats/playbooks"


def format_playbook(fid):
    """(the playbook page, its path) for the run's format, or ("", "") — video-system sync T9, 2026-10-21: the
    teardown's playbook hook builds a format playbook and nothing in writing read it. Read by path, never
    imported: the family's rendered page, or for a variant its family's page plus the variant's overrides."""
    fid = (fid or "").replace("new:", "").strip()
    if not fid or fid == "unknown":
        return "", ""
    own = PLAYBOOKS / f"{fid}.md"
    if own.is_file():
        return playbook_for_writing(own.read_text()), f"video-production formats/playbooks/{own.name}"
    for fam in sorted(PLAYBOOKS.glob("*.json")):
        try:
            j = json.loads(fam.read_text())
        except ValueError:
            continue
        # a retired (deprecated) variant is never a run's playbook (formats/workflow-layout.md, 2026-11-27)
        var = next((v for v in j.get("variants") or [] if isinstance(v, dict) and v.get("id") == fid
                    and v.get("status") != "deprecated"), None)
        page = fam.with_suffix(".md")
        if var and page.is_file():
            over = json.dumps(var.get("overrides") or {}, indent=1, ensure_ascii=False)
            return (playbook_for_writing(page.read_text(), fid) + f"\n\n**This run's format `{fid}` is a variant of it; "
                    f"its overrides:**\n\n```json\n{over}\n```\n"), \
                f"video-production formats/playbooks/{page.name}, variant `{fid}`"
    return "", ""


def playbook_for_writing(page, variant=None):
    """Only what the writing uses of a playbook page (VIDEO-RULINGS V22, sync W33, 2026-10-21): its title and
    what it is, the structural signature, what is specialised and why, and this run's own variant row. The
    stage settings, failures, cost, quality bar, the other variants and the history are production's."""
    head = re.split(r"(?m)^## ", page, maxsplit=1)[0]
    head = "\n".join(l for l in head.splitlines()
                     if not l.startswith(("*Rendered from", "> Which model"))).strip()
    parts = {}
    for sec in re.split(r"(?m)^(?=## )", page)[1:]:
        parts[sec.splitlines()[0][3:].strip()] = sec.strip()
    keep = [head] + [parts[k] for k in ("Structural signature", "What is specialised, and why") if k in parts]
    if variant and "Variants (same workflow, refined)" in parts:
        m = re.search(r"(?ms)^### [^\n]*\(`" + re.escape(variant) + r"`[^\n]*\n.*?(?=^### |\Z)",
                      parts["Variants (same workflow, refined)"])
        if m:
            keep.append("## This run's variant\n\n" + m.group(0).strip())
    return "\n\n".join(keep) + "\n"


def hooks_for_build(text):
    """The hook set as the build pass reads it (V22, sync W33): the reading, the foundational hook and the
    control in full — the body is built from the control — and each variation's TAKE, LINE and CARD, which
    is what its HOOK COMPATIBILITY line checks. The variations' scroll stoppers, receipts and the hook tests
    go on to the brief, which reads the hooks whole. Unchanged when the answer is not in the expected shape."""
    i = text.find("=== PART 2: HOOKS ===")
    v = text.find("**3. THE FIVE VARIATIONS**", i) if i >= 0 else -1
    if i < 0 or v < 0:
        return text
    tests = re.search(r"(?m)^\*\*THE FORMAT TEST\*\*", text[v:])
    end = v + tests.start() if tests else len(text)
    rows = [l for l in text[v:end].splitlines()
            if re.match(r"\s*(\*\*V\d|\*\*3\. THE FIVE VARIATIONS|(TAKE|LINE|CARD) V\d+:)", l)]
    more = re.search(r"(?m)^\*\*4\. BRIEF VARIATION OPPORTUNITIES\*\*.*?(?=^## |\Z)", text[end:], re.S)
    return (text[:v] + "\n".join(rows) + "\n\n(Each variation as the body's compatibility check needs it — "
            "its take, line and card. Its scroll stopper, thumbnail, receipts and the hook tests are carried "
            "whole to the brief.)\n\n" + (more.group(0).strip() + "\n" if more else ""))


def ask_lane(st):
    """The run's lane and its ask, for every pass (video-system sync W12, 2026-10-21). The lane is the one
    declared on the run (teardown --lane), else the brand's Settings default — read through product_pick,
    the teardown's lane reader. It changes only the ask and the pace of the pitch, never the product (V1)."""
    import product_pick as PP
    lane, why = PP.lane_of(st.get("brand") or "", (st.get("lane_declared") or os.environ.get("VT_LANE") or "").lower())
    if lane == "organic":
        ask = ("organic — the last ask is: comment the word (ONE word the piece itself already says — the "
               "product's or the problem's plain name — printed in capitals in the ask, the viewer gets the link "
               "back), or follow. Never a button, never a URL.")
    elif lane == "paid":
        ask = ("paid — the last ask is: tap the button below and buy, in words the offer file allows. "
               "Never a comment or follow ask as the last ask.")
    else:
        ask = ("[UNFILLED] — no lane was declared on this run and the brand's Settings name no default. Write "
               "the piece exactly as for both lanes (same product, same claims, same close); end on the paid ask "
               "(tap the button), and say in the piece's risks that the lane was not declared.")
    return f"- **LANE:** {ask}\n- **Where it came from:** {why}"


def run_inputs(st):
    """The 2026-10-21 run-time inputs every writing prompt may ask for, filled for any route (verify row 10):
    {ask_lane}, {video_spice} and {realism_index}. writing v2 fills them itself; the teardown's v1 stage loop
    (creator and founder runs, and --writing v1) calls this so its prompts get the very same text."""
    return {"ask_lane": ask_lane(st), "video_spice": video_spice(), "realism_index": realism_rows(st),
            "creative_controls": creative_controls(), "emotion_video_lines": emotion_video_lines(),
            "controls_target": controls_target(st), "creative_moves": _read(HERE.parent / "creative-moves.md"),
            "owner_notes": _read(HERE.parent / "owner-notes.md"), "winner_lane": winner_lane(st),
            "product_route": product_route(st),
            "declared_layers": declared_layers(st), "winners_feed": winners_feed(st),
            "edit_lessons": edit_lessons(st), "winner_breakdown": winner_breakdown(st),
            "decision_trail": decision_trail(st)}


def _trail_kit():
    kit = str(WS / "components" / "run-kit")
    if kit not in sys.path:
        sys.path.append(kit)   # appended, never ahead of this machine
    from run_kit import trail as T
    return T


def decision_trail(st):
    """`{decision_trail}`: why the run got here, every earlier stage's choice and reason (run-kit trail.block),
    NONE when the run has none. Inert until a prompt asks for it."""
    T = _trail_kit()
    return T.block(T.rows(st or {}))


def piece_keys(key, d, out):
    """The brief carries the thinking (logic layer W0): `piece.trail`, `piece.idea` and `piece.concept` are written
    once, in code, the moment the stage-5 writer call lands the brief, before anything stamps or hashes it
    (swipe_match.brief_hash and the acceptance stamp hash the whole block). Never appended later; keys a writer
    already set are kept. Only the stage-5 brief with a scene block."""
    if key != "stage5":
        return
    text = Path(out).read_text()
    blocks = list(re.finditer(r"```json\s*\n(.*?)\n```", text, re.S))
    if not blocks:
        return
    m = blocks[-1]
    try:
        doc = json.loads(m.group(1))
    except ValueError:
        return
    if not isinstance(doc, dict) or "scenes" not in doc:
        return
    st = json.loads((Path(d) / "run.json").read_text())
    idea = _read(Path(d) / "stages" / "4i-controlling-idea.md")
    piece = doc.setdefault("piece", {})
    piece.setdefault("trail", _trail_kit().rows(st))
    under = re.search(r"(?m)^#+\s*THE CONTROLLING IDEA\s*$\n+([^\n#][^\n]*)", idea)   # the line under the heading
    concept = (re.search(r"(?m)^CONCEPT:\s*(.+)$", idea) or [None, ""])[1].strip()
    piece.setdefault("idea", under.group(1).strip() if under else "")
    piece.setdefault("concept", "" if concept.lower() in ("none", "none on file") else concept)
    Path(out).write_text(text[:m.start(1)] + json.dumps(doc, indent=1, ensure_ascii=False) + text[m.end(1):])


# ------------------------------------------------------------------ what the later stations hand back (2026-11-18)
# Results reached the writing through one file, read by one v1 stage (the hook stage's {winners}); the v2 passes
# read nothing, and what the edit learned and how a winner breaks down were kept and read by no prompt. These
# three inputs put that data in reach of every pass on every route. Each is a plain read of a file another
# station owns (never written here), says NONE in words when there is nothing yet, and never stops a run.
# A prompt gets one only by asking for its slot.

NONE_YET = "NONE"


def winners_feed(st):
    """`{winners_feed}`: what the results taught, for this brand (runs/winners/<brand>/taught.md, written by the
    winners side): the top ad per angle, the desk's calls, the send-back reasons, the score per prompt version.
    NONE when the brand has none yet."""
    f = WS / "runs" / "winners" / str((st or {}).get("brand") or "") / "taught.md"
    return _read(f).strip() or f"{NONE_YET} — nothing taught yet for this brand (runs/winners/<brand>/taught.md)."


LESSON_STAGES = ("brief", "writing", "teardown")


def edit_lessons(st):
    """`{edit_lessons}`: what the cut has taught that the writing can act on. Two reads of video-edit's own
    files: the standing rules it keeps (components/video-edit/learned.json `rules`, the ones not scoped to the
    edit alone) and the lessons bank rows filed for a writing-side stage (runs/video-edit/_lessons/
    lessons.jsonl, `stage` brief, writing or teardown), newest first, this brand's and brand-free rows."""
    brand = str((st or {}).get("brand") or "")
    out = []
    try:
        rules = json.loads(_read(WS / "components/video-edit/learned.json") or "{}").get("rules") or []
    except ValueError:
        rules = []
    for r in rules:
        if not isinstance(r, dict) or not r.get("rule"):
            continue
        if str(r.get("stage") or "") in LESSON_STAGES or any(w in str(r.get("scope") or "").lower() for w in LESSON_STAGES):
            out.append(f"- (standing rule) {r['rule']}")
    rows = []
    for line in _read(WS / "runs" / "video-edit" / "_lessons" / "lessons.jsonl").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and str(r.get("stage") or "") in LESSON_STAGES \
                and str(r.get("brand") or brand) == brand and (r.get("lesson") or r.get("rule") or r.get("what")):
            rows.append(r)
    for r in rows[::-1][:20]:
        out.append(f"- ({r.get('stage')}) {r.get('lesson') or r.get('rule') or r.get('what')}"
                   + (f" [{r.get('at') or r.get('run') or ''}]" if r.get("at") or r.get("run") else ""))
    return "\n".join(out) or f"{NONE_YET} — the edit has filed no lesson for the writing yet."


def winner_breakdown(st):
    """`{winner_breakdown}`: the brand's top ad taken apart part by part (hook, lead, offer, mechanism, outcome,
    features against benefits, guarantee, ask, then the scenes with the sound off; its type and angle; what to
    change), as the winners side writes it: runs/winners/<brand>/breakdown.md."""
    f = WS / "runs" / "winners" / str((st or {}).get("brand") or "") / "breakdown.md"
    return _read(f).strip() or f"{NONE_YET} — no winner has been taken apart for this brand yet (runs/winners/<brand>/breakdown.md)."



def product_route(st):
    """THE PRODUCT ROUTE, decided by the style (owner, 2026-11-18). The triage names the swipe's style; the style
    bank (components/video-production/styles/bank.json) puts every style in a family, and its `product_route` map
    says what the product is in that family: `in-scene` (photoreal, and a style not in the bank: the product is in every
    made shot it appears in, from its casting sheet; VIDEO-RULINGS V59, 2026-11-25) or `in-look` (handmade, drawn, 3d:
    the product is generated in the ad's own look from its 3D build)."""
    sid = (st or {}).get("style_id") or ""
    try:
        bank = json.loads(_read(WS / "components/video-production/styles/bank.json"))
    except (ValueError, TypeError):
        bank = {}
    fam = next((s.get("family") for s in bank.get("styles") or [] if s.get("id") == sid), None)
    pr = bank.get("product_route") or {}
    route = pr.get(fam) or pr.get("unknown") or "real"
    why = pr.get("routes", {}).get(route, "")
    head = (f"PRODUCT ROUTE: {route.upper()} — style `{sid or 'unknown'}`, family `{fam or 'unknown'}`"
            + ("" if fam else " (style not in the bank: filmed, so the product is in the shot)") + ".")
    if route == "in-scene":
        return (head + "\n" + why + "\n\nThis OVERRIDES every line below that says the product is never generated, that its "
                "place is left clear, that a grip is left open for it, that no packshot rides into a job, or that the real "
                "product photo or footage is laid on at the edit. In this brief: every made shot that shows or uses the product "
                "has it IN the frame, in the hand, on the skin or standing where the shot puts it. `first_frame`, every shot's "
                "`start_picture`, gestures and `ends_on` say so plainly (\"holds the brush to his cheek\", never \"grip open "
                "for the brush\", \"place left clear\", \"space reserved\", \"composite\", \"laid on at the edit\", \"never "
                "generated\"). Its name goes in that shot's `refs` beside the cast sheet. PRODUCT LOCK lines name the shot, the "
                "hand and the action and end \"in the shot, from its casting sheet\". A shot that only shows what the product "
                "holds says \"texture only, no pack\". Never write the swipe's own product, its container or how its person "
                "uses it into our action. A shot cut from our own footage stays that footage. The END CARD keeps the real "
                "product photo, and words on screen are still laid on at the edit.")
    if route != "in-look":
        return head + "\n" + why
    return (head + "\n" + why + "\n\nThis OVERRIDES every line below that says the product is never generated, that its "
            "place is left clear, that no packshot rides into a job, or that the real product photo or footage is laid "
            "on at the edit. In this brief: the product is IN the frame of every job it appears in, rendered in the "
            "ad's look; its reference is the product's 3D build render (from its 3D kit), never a real photo pasted "
            "on; PRODUCT LOCK lines end \"rendered in the ad's look from its 3D build, in the generation\"; the END "
            "CARD plate holds the product rendered in the look. Words on screen are still laid on at the edit.")


def winner_match_step(d, st):
    """Stage 2w through `winner_match.on_chain` (loaded beside this file). (go, why). `VW_WINNER_MATCH_OFF=1` turns
    it off for one shell (the rollback)."""
    if os.environ.get("VW_WINNER_MATCH_OFF"):
        return True, ""
    import importlib.util
    sp = importlib.util.spec_from_file_location("vw_winner_match", Path(__file__).resolve().parent / "winner_match.py")
    mod = importlib.util.module_from_spec(sp)
    try:
        sp.loader.exec_module(mod)
    except Exception as e:  # noqa: BLE001  (a match that cannot load never stops the writing)
        st.setdefault("stages", {})["stage2w"] = dict(status="error", name="Winner match", error=str(e)[:300])
        return True, ""
    return mod.on_chain(d, st)


def winner_shape(brand, slug):
    """The winner's story shape as its section plan: the arc its shape call named (runs/winners/<brand>/shapes/
    shapes.json, `winners.py shapes build`), each arc beat with the doctrine section it holds (creative-controls
    controls.json `arcs`). '' when the brand has no shape calls or this winner has none."""
    sj = _json_or(WS / "runs" / "winners" / str(brand or "") / "shapes" / "shapes.json")
    w = next((x for x in sj.get("winners") or [] if x.get("run") == slug or slug in (x.get("folded_copies") or [])), None)
    if not w or not w.get("arc"):
        return ""
    arcs = {a.get("id"): a for a in _json_or(WS / "components" / "creative-controls" / "controls.json").get("arcs") or []}
    beats = (arcs.get(w["arc"]) or {}).get("beats") or []
    plan = " → ".join(f"{b.get('beat')} [{b.get('section')}]" for b in beats) or " → ".join(w.get("arc_beats") or [])
    return (f"WINNER SHAPE: {w['arc']} ({w.get('arc_fit') or '?'} fit). {w.get('arc_why') or ''}".rstrip() +
            f"\nWINNER SHAPE, BEAT BY BEAT (beat [doctrine section]): {plan}" +
            ("\nWINNER DEVICES: " + ", ".join(w["devices"]) if w.get("devices") else "") +
            ("\nWINNER TELLER: the founder. Carry the shape, never the founder as teller in new work."
             if "founder" in str(w.get("teller") or "").lower() else ""))


def _json_or(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


def winner_lane(st):
    """THE WRITING LANE (owner, 2026-11-08). Winner + swipe: the brand's proven ad, word for word, with what
    made it work, read beside the swipe. Swipe only: a new brand or offer with no winner yet."""
    wl = st.get("writing_lane") or {}
    if wl.get("lane") != "winner":
        return ("LANE: SWIPE ONLY. This brand or offer has no proven ad yet. Write from the swipe and the "
                "brand's own messaging (product, avatar, language bank) alone.")
    slug = wl.get("winner") or ""
    rd = WS / "runs" / "video-teardown" / "_work" / slug
    words = _read(rd / "stages" / "1-transcript.md") or _read(rd / "stages" / "1-teardown.md")[:12000]
    try:
        doc = json.loads((rd / "doctrine.json").read_text())
    except (OSError, ValueError):
        doc = {}
    secs = " → ".join(f"{x.get('id')} ({x.get('span')})" for x in doc.get("sections_carried") or [])
    if not doc:     # newer teardowns keep the read in stages/1c-doctrine.md, not doctrine.json: read it from there
        try:
            import importlib.util
            sp = importlib.util.spec_from_file_location("vw_winner_index", Path(__file__).resolve().parent / "winner_index.py")
            wi = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(wi)
            idx = {}
            for f in (WS / "runs" / "winners").glob("*/winner-index.json"):    # the index borrows a copy's read
                idx.update({r["run"]: r.get("traits") or {} for r in json.loads(f.read_text()).get("winners") or []})
            t = idx.get(slug) or wi.traits(slug) or {}
        except Exception:  # noqa: BLE001
            t = {}
        doc = {"framework": t.get("framework_full") or "unknown",
               "awareness": {"entry": t.get("aware_in") or "?", "exit": t.get("aware_out") or "?"}}
        secs = " → ".join(t.get("sections") or [])
    # the winner's own core message, off its teardown and spec (2026-11-25); '' on a teardown that wrote none
    try:
        import importlib.util
        sp = importlib.util.spec_from_file_location("vw_winner_message", Path(__file__).resolve().parent / "winner_index.py")
        wm = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(wm)
        said = wm.message_text(slug)
    except Exception:  # noqa: BLE001
        said = ""
    return ("LANE: WINNER + SWIPE. The brand's proven ad is `" + slug + "`. Carry its message into the swipe: "
            "its angle, its mechanism, its proof and the customer words that made it sell, inside the swipe's "
            "structure. The swipe gives the form; the winner gives what we say.\n\n"
            f"WINNER FRAMEWORK: {doc.get('framework', 'unknown')}\n"
            f"WINNER AWARENESS: {(doc.get('awareness') or {}).get('entry', '?')} → {(doc.get('awareness') or {}).get('exit', '?')}\n"
            f"WINNER SECTIONS: {secs or 'unknown'}\n\n" + (said + "\n\n" if said else "") +
            (winner_shape(st.get("brand"), slug) + "\n\n" if winner_shape(st.get("brand"), slug) else "") +
            f"WINNER, WORD FOR WORD:\n{words or '(transcript missing)'}")


def _controls():
    """components/creative-controls/creative_controls.py, loaded by path (it is the one place the dials live)."""
    import importlib.util
    sp = importlib.util.spec_from_file_location("vw_creative_controls", WS / "components/creative-controls/creative_controls.py")
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return mod


def creative_controls():
    """The VIDEO side of the creative controls (VIDEO-RULINGS V47): each video dial with the scale and what it does on
    camera, the guards, and the never-sterile floor, read from components/creative-controls/controls.json — the one place
    the dials live. (The whole slice is 58 KB and written for copy; the writer of a video needs the video lines.) An input
    that cannot be read is said in the text and the pass still runs (V34)."""
    try:
        c = json.loads(_read(WS / "components/creative-controls/controls.json"))
    except (ValueError, TypeError):
        return "[UNFILLED] — components/creative-controls/controls.json not found or unreadable"
    out = ["THE VIDEO DIALS — each one: what it is, its scale, and what it does on camera.", ""]
    for d in c.get("dials") or []:
        if "video" not in (d.get("media") or []):
            continue
        scale = " · ".join(f"{s['level']} {s['name']}" for s in d.get("scale") or [])
        out.append(f"- **{d['name']}** (`{d['id']}`): {d.get('what', '')} Scale: {scale}. On camera: {d.get('video', '')}"
                   + (f" Risk: {d['risk']}" if d.get("risk") else ""))
    out += ["", "GUARDS — moves that must hold whatever the dials say:"]
    out += [f"- **{g['name']}**: {g.get('what') or g.get('move') or ''}" for g in c.get("guards") or []]
    fl = c.get("floor") or {}
    if fl:
        out += ["", "THE FLOOR — " + str(fl.get("what", "")), "Minimum levels: "
                + ", ".join(f"{k} {v}" for k, v in (fl.get("levels") or {}).items())]
    out += story_lines(c)
    return "\n".join(out)


def story_lines(c):
    """The story layer (2026-10-28, owner: "amplify creative storytelling abilities, conversion, amplification,
    dramatization ... take this all the way to the edge"): the arcs, the story devices, the persuasion triggers and the
    edge line, read from controls.json, one line each — so the writer picks an arc and its devices by name."""
    if not c.get("arcs"):
        return []
    out = ["", "STORY ARCS — " + c.get("arc_rule", "")]
    out += [f"- **{a['name']}** (`{a['id']}`; best for {', '.join(a['best_for'])}): {a['what']} {a['how']} Beats → sections: "
            + " → ".join(f"{b['beat']} (`{b['section']}`)" for b in a["beats"]) for a in c["arcs"]]
    out += ["", "STORY DEVICES — " + c.get("device_rule", "")]
    out += [f"- **{d['name']}** (`{d['id']}`, {d['family']}): {d['what']} How: {d['how']}" for d in c.get("story_devices") or []]
    out += ["", "PERSUASION TRIGGERS — " + c.get("trigger_rule", "")]
    out += [f"- **{t['name']}** (`{t['id']}`): {t['what']} How: {t['how']} The line: {t['line']}" for t in c.get("persuasion_triggers") or []]
    e = c.get("edge_line") or {}
    if e:
        out += ["", "THE EDGE — " + e.get("what", ""), "Push: " + "; ".join(e.get("push") or []),
                "Never: " + "; ".join(e.get("never") or [])]
    out += ["", "HOW THE STORY PULLS ON THE DIALS:"]
    out += [f"- {r['rule']}" for r in c.get("story_interactions") or []]
    return out


def emotion_video_lines():
    """The 12 emotions and how each looks on camera (controls.json emotions[].video) — what `face` and `gestures` are written from."""
    try:
        em = json.loads(_read(WS / "components/creative-controls/controls.json") or "{}").get("emotions") or []
    except ValueError:
        em = []
    if not em:
        return "[UNFILLED] — the emotion bank has no video lines"
    return "\n".join(f"- `{e['id']}` ({e.get('name', e['id'])}): {e.get('video', '')}" for e in em)


# THE DIAL PRESET FOLLOWS THE AWARENESS LEVEL (logic layer W1, 2026-11-18). Every run aimed at the house preset
# whatever it was for, with no reason given for this brief. The creative controls already hold a preset per
# level; the run's own awareness level now picks it, the reason is kept on the run (`controls_preset`) and on
# the trail, and the hook check and the director read the same record, so one run never aims at two presets.
# A level with no preset of its own, or a run with no level yet, stays on the house preset and says so. A run
# whose writing had already started when this landed stays on the house preset it was written to.
HOUSE_PRESET = "maxed"
# THE RULE IS WRITTEN AND OFF until the owner rules it on (review, 2026-11-18): a preset other than the house one
# changes what the live injection, hooks, spice and brief prompts aim at (the unaware preset reads "no offer, no
# call to action"), and every preset is still a draft. Off, every run aims at the house preset exactly as before
# and nothing is kept or noted. On (True here, or VW_PRESET_BY_AWARENESS=1 for one shell), it runs as below.
PRESET_FOLLOWS_AWARENESS = False


def preset_rule_on():
    return PRESET_FOLLOWS_AWARENESS or os.environ.get("VW_PRESET_BY_AWARENESS", "").strip() == "1"


PRESET_BY_AWARENESS = {"unaware": "native-unaware", "problem-aware": "problem-aware",
                       "product-aware": "product-proof", "most-aware": "product-proof"}
AWARENESS_LEVELS = ("most-aware", "product-aware", "solution-aware", "problem-aware", "unaware")
WRITTEN_KEYS = ("stage3", "stage4i", "stage4v2a", "stage4b", "stage4v2b", "stage4a", "stage4e", "stage4g", "stage5")


def run_awareness(st, d=None):
    """The level the run is written at: the audience stage's market state (a declared level is already in it),
    else the swipe's own entry level from the doctrine read. None when neither names one."""
    lv = str(((st or {}).get("market_state") or {}).get("awareness") or "").strip().lower()
    if not lv and d is not None:
        try:
            doc = json.loads((Path(d) / "doctrine.json").read_text())
            lv = str(((doc.get("awareness") or {}) if isinstance(doc, dict) else {}).get("entry") or "").strip().lower()
        except (OSError, ValueError, AttributeError):
            lv = ""
    lv = lv.split()[0].strip("`.,;") if lv else ""
    return lv if lv in AWARENESS_LEVELS else None


def _writing_started(st):
    """A writing pass has written something: done, or held with its answer on disk. A hold before any pass wrote
    (no lane picked, a new format waiting) is not writing."""
    for k in WRITTEN_KEYS:
        r = ((st or {}).get("stages") or {}).get(k) or {}
        if r.get("status") == "done" or (r.get("status") == "held" and r.get("out")):
            return True
    return False


def controls_preset(st, d=None):
    """(preset id, why, awareness level) for this run. The run's own record wins, so a run keeps one preset."""
    st = st if isinstance(st, dict) else {}
    rec = st.get("controls_preset") or {}
    if rec.get("preset"):
        return rec["preset"], rec.get("why") or "", rec.get("awareness")
    level = run_awareness(st, d)
    if not preset_rule_on():
        return HOUSE_PRESET, "the house preset (the awareness rule is written and not switched on)", level
    if _writing_started(st):
        return HOUSE_PRESET, ("this run's writing had started before the preset followed the awareness level; "
                              "it stays on the house preset it was written to"), level
    try:
        known = {p["id"]: p for p in _controls().load().get("presets") or []}
    except Exception:   # noqa: BLE001 — the dials file said unreadable below, where the target is read
        known = {}
    pid = PRESET_BY_AWARENESS.get(level or "")
    if pid and pid in known:
        return pid, f"this run enters at {level}; the {known[pid].get('name') or pid} preset is the one written for that level", level
    if level:
        return HOUSE_PRESET, f"this run enters at {level}; no preset is written for that level, so the house preset stands", level
    return HOUSE_PRESET, "no awareness level is on the run yet, so the house preset stands", level


def keep_controls_preset(st, d=None):
    """Choose the preset once and keep it on the run, with its row on the trail. -> the preset id.
    A run with no awareness level yet and no writing done has decided nothing: nothing is kept and nothing
    is noted, so the choice is made when the level is known."""
    pid, why, level = controls_preset(st, d)
    if not preset_rule_on() or (level is None and not _writing_started(st)):
        return pid
    if isinstance(st, dict) and not (st.get("controls_preset") or {}).get("preset"):
        st["controls_preset"] = {"preset": pid, "why": why, "awareness": level}
        try:
            import run as R
            R.trail_add(st, "writing", "Dial preset", pid, why, "the awareness rule")
        except Exception:   # noqa: BLE001 — the note is not worth a stopped pass
            pass
    return pid


def controls_target(st):
    """The VIDEO dials' levels to aim for: every video dial's default, the run's preset on top (chosen by its
    awareness level, controls_preset), the saved brand levels, the never-sterile floor (creative_controls.target).
    One line per dial; the brief turns them into face, gestures, camera, timing. A pure read: the preset is
    chosen and kept by run_writing (keep_controls_preset), and its reason lives on the run and the trail, never in
    the prompt text, so a resumed run's prompt is unchanged."""
    try:
        return _controls().target_md(controls_preset(st)[0], (st or {}).get("brand"), "video")
    except Exception as e:   # noqa: BLE001 — an unreadable input is said, not fatal
        return f"[UNFILLED] — the video dial levels could not be read ({str(e)[:100]})"


def video_spice():
    """VIDEO-SPICE.md, whole — the seven layers and the levels (V9)."""
    return _read(WS / "components/video-production/VIDEO-SPICE.md").strip() or "[UNFILLED] — VIDEO-SPICE.md not found"


def realism_rows(st):
    """The realism index's WRITING-stage rows (stage `writing`, or `writing` in `also`), this run's format first.
    The index is video-production's definition file (spice/realism-index.json); it is read, never written."""
    try:
        j = json.loads(_read(WS / "components/video-production/spice/realism-index.json") or "{}")
    except ValueError:
        return "[UNFILLED] — the realism index does not parse"
    fid = ((st.get("layers") or {}).get("format") or st.get("format_id") or "").replace("new:", "")
    rows = [r for r in j.get("rows") or [] if isinstance(r, dict) and
            (r.get("stage") == "writing" or "writing" in (r.get("also") or []))]
    if not rows:
        return "[UNFILLED] — the realism index has no writing-stage rows"
    rows.sort(key=lambda r: (fid not in (r.get("formats") or []), r.get("level") or 9, r.get("id") or ""))
    out = []
    for r in rows:
        fm = ", ".join(r.get("formats") or []) or "every format"
        mine = " · THIS FORMAT" if fid and fid in (r.get("formats") or []) else ""
        out.append(f"- `{r.get('id')}` · {r.get('family')} · level {r.get('level')} · formats: {fm}{mine}"
                   + (f" · culture: {r['culture']}" if r.get("culture") else "")
                   + f"\n  what you see: {r.get('what_you_see') or ''}\n  its words: {r.get('prompt') or ''}")
    return "\n".join(out)


def apply_call(d, st):
    """owner's call on a new format, applied before writing (review, 19 Oct): "Same as X" (fold) writes it as
    format X; "Not a format" (drop) writes it with no format, from the doctrine's structure; "Its own format"
    (own) keeps the new name. Calls answered are taken off the waiting list."""
    import layers as L
    lay = st.setdefault("layers", {})
    fid = lay.get("format") or st.get("format_id") or ""
    c = L.call_for(fid) if fid.startswith("new:") else None
    if c and c.get("decision") == "fold" and c.get("into"):
        lay["format"] = st["format_id"] = c["into"]
    elif c and c.get("decision") == "drop":
        lay["format"] = st["format_id"] = None
    if st.get("layers_pending"):
        st["layers_pending"] = [p for p in st["layers_pending"] if not L.call_for(p)]
    try:
        (Path(d) / "run.json").write_text(json.dumps(st, indent=2, ensure_ascii=False))
    except OSError:
        pass
    return st


FORMAT_CALL_GUIDANCE = C.CM / "prompts" / "reference" / "format-call-guidance-v1-owner.md"


def format_call_guidance():
    """How to decide on a format the lists do not know (owner approved 2026-11-19): printed with every stop on a
    new format, so whoever makes the call sees the rule beside it. Empty when the file is not there."""
    text = _read(FORMAT_CALL_GUIDANCE)
    return "\n".join(l for l in text.splitlines() if l.strip() and not l.startswith("<!--")).strip()


def format_approved(st):
    """A format the bank does not have ('new:<name>') stops for owner's call. Read through the
    teardown's one call reader (layers.call_for, 2026-10-19): it used to look for a shape Outlier
    never writes, so a call made on the Swipes tab never released the run."""
    import layers as L
    if any(not L.call_for(p) for p in (st.get("layers_pending") or [])):
        return False                      # a new layer still waits for owner's call
    fid = (st.get("layers") or {}).get("format") or st.get("format_id") or ""
    if not fid.startswith("new:"):
        return True
    return L.call_for(fid) is not None


def prompt_version(p):
    """The -vN- in the prompt's filename (stage4v2a-readhooks-v8-owner.md -> 8); 2 when it has none."""
    m = C.VERSION.search(Path(p).name)
    return int(m.group(1)) if m else 2


def plan(brand, route, lane):
    """v2's stage dicts, with v1's bindings for the same work."""
    v1 = {s["key"]: s for s in C.stages(brand, "", route, lane)}
    pool = C.known_sources()
    out = []
    import visuals
    for key, sid, fid, name, prompt, splits in PASSES:
        if key == "stage5" and visuals.ours("brief"):
            prompt = STAGE5_STAGED_FRESH               # switched on: staged fresh, the swipe as understanding only
        p = V2 / prompt
        src_keys = [x[1] for x in splits] if splits else [key]
        vars_ = {}
        for k in src_keys:
            vars_.update((v1.get(k) or {}).get("vars") or {})
        asks = set(re.findall(r"\{([a-z0-9_]+)\}", p.read_text()))
        for g in sorted(asks - set(vars_)):
            if g in pool:
                vars_[g] = pool[g]
        for run_input in RUN_INPUTS:
            vars_[run_input] = "~" + run_input
        if key == "stage4v2b":
            vars_["hook_set"] = "@stage4v2a"          # its reading + hooks, as one block
        if key == "stage4e":
            vars_.update(full_script="@stage4d", placement_plan="@stage4a")
        if key == "stage4i":
            vars_["baseline_injection"] = "@stage3"
        else:
            vars_["controlling_idea"] = "@stage4i"    # V56: every pass after it writes inside the one idea
        vars_ = {k: v for k, v in vars_.items() if k in asks}
        if route and "production_route" in vars_:
            vars_["production_route"] = "=" + ("AI" if route.lower() == "ai" else route.lower())
        base = v1.get(key) or {}
        out.append(dict(key=key, id=sid, file_id=fid, name=name, group="Writing v2", blurb="",
                        prompt=str(p), version=prompt_version(p), engine="claude", vars=vars_,
                        per_run=sorted(C.PER_RUN & set(vars_)), role="stage", search=False,
                        model="opus", splits=splits, config_prompt=base.get("config_prompt")))
    return out


# ------------------------------------------------------------------ split

_REASON_MISS = re.compile(r"^(V\d): (\w+) differs from shared target (\d+) without a reason$")
_LEVEL_MISS = re.compile(r"^(V\d): missing or invalid (\w+) level$")
_EVIDENCE_MISS = re.compile(r"^(V\d): (\w+) needs visible or audible evidence$")
_SMALL = (_REASON_MISS, _LEVEL_MISS, _EVIDENCE_MISS)


def _reasons_only(problems):
    """True when every problem in a hook check is a small gap in one dial's entry: its written reason for a level off
    target, its level, or its evidence. The openings themselves are fine."""
    return bool(problems) and all(any(rx.match(p) for rx in _SMALL) for p in problems)


def _repair_reasons(path, problems):
    """Ask the writer, once, for only the missing parts of the named dial entries in a hook-matrix (a level on the
    dial's own scale, its evidence, its reason when off target), from each opening's own line, scroll and evidence;
    write them into the matrix and keep the old file beside it. Nothing else changes. True when every one came back."""
    import run as R
    text = path.read_text()
    m = re.search(r"```hook-matrix\s*\n(.*?)\n```", text, re.S)
    if not m:
        return False
    matrix = json.loads(m.group(1))
    rows = {r.get("id"): r for r in matrix.get("openings") or []}
    asks = []
    for p in problems:
        g = next(rx.match(p) for rx in _SMALL if rx.match(p))
        row = rows.get(g[1]) or {}
        sc = (row.get("controls") or {}).get(g[2]) or {}
        asks.append({"id": g[1], "dial": g[2], "missing": p.split(": ", 1)[1], "entry_now": sc,
                     "target": int(g[3]) if g.re is _REASON_MISS else None,
                     "line": row.get("line"), "scroll": row.get("scroll")})
    prompt = ("You wrote these hook openings. Each item below is one dial entry with a part left out (named in `missing`). "
              "Fill only that part, from the opening's own line, scroll and the entry as it is: a missing level is a whole "
              "number on that dial's scale; evidence is the specific word, object, action, camera or sound that shows it; "
              "a reason says why this opening's format calls for a level that differs from the set's target. Change "
              "nothing else.\n\nAnswer with only a JSON object mapping \"<id>.<dial>\" to an object with the fields you "
              "filled (level, evidence, exception).\n\n" + json.dumps(asks, indent=1, ensure_ascii=False, default=str))
    try:
        r = R._claude_run(["--model", "sonnet", "--allowed-tools", "", "--output-format", "json"], prompt, timeout=300)
        out = json.loads(r.stdout).get("result") or ""
        got = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
    except Exception:  # noqa: BLE001 -- a repair that cannot run leaves the hold as it was
        return False
    for a in asks:
        fix = got.get("%s.%s" % (a["id"], a["dial"]))
        if isinstance(fix, str):
            fix = {"exception": fix}
        if not isinstance(fix, dict) or not fix:
            return False
        ent = rows[a["id"]].setdefault("controls", {}).setdefault(a["dial"], {})
        for k in ("level", "evidence", "exception"):
            if k in fix and fix[k] not in (None, ""):
                ent[k] = int(fix[k]) if k == "level" and str(fix[k]).lstrip("-").isdigit() else fix[k]
    path.with_name(path.stem + ".before-reasons" + path.suffix).write_text(text)
    path.write_text(text[:m.start(1)] + json.dumps(matrix, indent=1, ensure_ascii=False) + text[m.end(1):])
    return True


def decided_hooks(d, st, matrix, problems):
    """AUTONOMOUS RUNS (owner, 2026-11-27: "i need this process to be autonomous"): a hook matrix still failing after
    its one remake goes to the decision layer (video-teardown decide.py) instead of stopping the run, the same way the
    structure, hook-format, audit and swipe-match holds do. Only when the layer is on for this run (VT_CHAIN=v2 and
    the writing stage on auto, e.g. run.py --autonomous) and the openings parsed; the call is filed for the owner to
    agree with or overrule, and the matrix carries the open findings. True when every finding was passed."""
    if not isinstance(matrix, dict) or not st.get("_v2_hook_remade"):
        return False
    try:
        import decide
    except ImportError:
        return False
    if not decide.on("hook"):
        return False
    items = [{"n": "HM%d" % (i + 1), "element": str(x)[:300], "status": "hook matrix"} for i, x in enumerate(problems)]
    if decide.auto(d, st, "hook", items):
        return False                                     # shadow mode: logged, the run still waits
    matrix["decided"] = [{"n": it["n"], "finding": it["element"]} for it in items]
    (Path(d) / "HOOK-FORMAT-decided.md").write_text(
        "# Hook matrix findings passed by the decision layer\n\nFiled in runs/decisions/calls.jsonl for the owner to "
        "agree with or overrule; the run continued.\n\n" + "\n".join("- %s: %s" % (it["n"], it["element"]) for it in items) + "\n")
    return True


def split(d, st, p):
    import run as R
    rec = st["stages"][p["key"]]
    body = (d / rec["out"]).read_text()
    marks = [(m.start(), m.end(), m.group(1).strip()) for m in
             re.finditer(r"(?m)^=== PART \d+: ([A-Z ]+) ===\s*$", body)]
    got = {}
    for i, (a, b, name) in enumerate(marks):
        got[name] = body[b:marks[i + 1][0] if i + 1 < len(marks) else len(body)].strip() + "\n"
    missing = [m for m, *_ in p["splits"] if m not in got]
    if missing:
        rec["status"] = "error"
        rec["error"] = "the merged answer is missing part(s): " + ", ".join(missing)
        R.save(d, st)
        raise RuntimeError(rec["error"])
    for marker, k1, f1, n1 in p["splits"]:
        out_name = f"stages/{f1}-{R.slug(n1)}.md"
        (d / out_name).write_text(got[marker])
        st["stages"][k1] = dict(status="done", name=n1, out=out_name, sent=rec.get("sent"),
                                engine="claude", model=rec.get("model"), v2_pass=p["key"],
                                prompt_name=rec.get("prompt_name"), finished=R.now(),
                                chars_out=len(got[marker]))
    R.save(d, st)
    # what v1 does after the same stages
    sr = None
    # every part's research blanks are filled before the audit reads the script (2026-10-21, sync W32): the
    # placement and the expansion used to keep theirs, and an unfilled blank sent the build back for round 2
    for k1 in ("stage4b", "stage4a", "stage4c", "stage4d"):
        if k1 not in [x[1] for x in p["splits"]]:
            continue
        out_name = st["stages"][k1]["out"]
        import importlib.util as _u
        if sr is None:
            _rp = _u.spec_from_file_location("slot_research", TD / "slot_research.py")
            sr = _u.module_from_spec(_rp); _rp.loader.exec_module(sr)
        if sr.markers((d / out_name).read_text()):
            try:
                res = sr.fill(d, stage_file=Path(out_name).name, find=sr.markers)
                R.say(f"      blanks in {k1}: {len(res['filled'])} of {res['holes']} filled by research")
            except Exception as e:
                R.say(f"      blank research could not run ({type(e).__name__}) — left marked")
        if k1 == "stage4b":
            # Each opening proves its shared dials and visual format before production.
            import hook_matrix
            matrix, problems = hook_matrix.from_text((d / out_name).read_text(), st.get("brand"),
                                                     preset=controls_preset(st, d)[0],
                                                     constraints=owner_controls.load(d))
            if problems and any("differs between prose and matrix" in x for x in problems):
                # THE MATRIX IS A COPY OF THE PROSE (2026-11-20): a reworded copy is set back to the prose, then checked
                fixed, n = hook_matrix.sync_to_prose((d / out_name).read_text())
                if n:
                    (d / out_name).write_text(fixed)
                    matrix, problems = hook_matrix.from_text(fixed, st.get("brand"), preset=controls_preset(st, d)[0],
                                                             constraints=owner_controls.load(d))
                    R.say(f"      hook copy: {n} field(s) set back to the prose")
            if problems and _reasons_only(problems):
                # A QUICK FIX FOR A SMALL MISS (owner, 2026-11-20: "when things just need quick fixes, we just should make
                # the quick fix"): the openings are fine and only the written reason for a dial set off its target is
                # missing. The writer is asked for just those reasons, once, and the check runs again on the result.
                if _repair_reasons(d / out_name, problems):
                    matrix, problems = hook_matrix.from_text((d / out_name).read_text(), st.get("brand"),
                                                             preset=controls_preset(st, d)[0],
                                                             constraints=owner_controls.load(d))
                    R.say("      hook reasons: %s" % ("filled by the writer, check passes" if not problems else "still open after one repair"))
            if problems and decided_hooks(d, st, matrix, problems):
                problems = []                            # the decision layer passed them; the run continues
            if problems:
                (d / "HOOK-FORMAT.md").write_text("# Hook matrix needs repair\n\n" + "\n".join(problems))
                st["stages"][k1]["status"] = "error"
                st["stages"][k1]["error"] = "; ".join(problems)
                R.save(d, st)
                raise RuntimeError("Hook creative controls / visual format: " + "; ".join(problems))
            # the preset the openings were checked against travels with the matrix, so production checks the same
            matrix = dict(matrix, controls_preset=controls_preset(st, d)[0]) if isinstance(matrix, dict) else matrix
            (d / "hook-matrix.json").write_text(json.dumps(matrix, indent=2) + "\n")
            R.structure_gate(d, st, "stage4b", (d / out_name).read_text())
    if "stage4a" in st["stages"] and st["stages"]["stage4a"].get("v2_pass") == p["key"]:
        v = C.product_entry((d / st["stages"]["stage4a"]["out"]).read_text())
        if v == "NONE":
            st["asset_type"] = "hook-asset"
            R.save(d, st)
            R.say("      product entry: NONE — this hands off; the brief becomes a hook asset")


# THE AUDIT'S RE-RUN BUILD IS A PATCH (2026-10-21, video-system sync W32). The build pass's own answer and
# the audit's numbered fixes go to one patch call that returns only the changed lines; they are applied and
# the SAME full audit reads the script again. A patch that cannot be applied exactly (a FIND that is not in
# the script once) is thrown away and the pass is rebuilt, as before. INJECTION and HOOKS re-runs still
# rebuild: every pass after them reads what they write.
PATCH_PROMPT = "stage4v2b-patch-v1-owner.md"
PATCH_BLOCK = re.compile(r"=== FIX ([^=\n]+?) ===[ \t]*\nPART:[^\n]*\nFIND:[ \t]*\n(.*?)\nREPLACE:[ \t]*\n(.*?)\n=== END ===", re.S)


def apply_patch(body, answer):
    """(the patched script, how many blocks) — or (None, why) when any block cannot be applied exactly."""
    blocks = PATCH_BLOCK.findall(answer or "")
    if not blocks:
        return None, "the patch answer has no FIX blocks"
    for label, find, repl in blocks:
        n = body.count(find)
        if n != 1:
            return None, f"FIX {label.strip()}: its FIND is in the script {n} times, not once"
        body = body.replace(find, repl, 1)
    return body, len(blocks)


def patch_build(d, st, p, words, extras):
    """True when the audit's fixes were patched into the build pass; False -> rebuild it as before."""
    import run as R
    rec = st["stages"].get(p["key"]) or {}
    f = d / (rec.get("out") or "")
    tpl = V2 / PATCH_PROMPT
    if not rec.get("out") or not f.is_file() or not tpl.is_file():
        return False
    body = f.read_text()
    prompt = (tpl.read_text().replace("{build_output}", body).replace("{audit_fixes}", words.strip())
              .replace("{ask_lane}", str((extras or {}).get("ask_lane") or "")))
    out = d / "stages" / f"{p['file_id']}-patch-{len(rec.get('patches') or []) + 1}.md"
    _CURRENT.clear()
    _CURRENT["key"] = p["key"] + "-patch"
    try:
        claude_v2(prompt, out, p.get("model"))
    except HandPromptMismatch:
        raise
    except RuntimeError as e:
        R.say(f"      the patch call stopped ({str(e)[:120]}) — rebuilding the pass instead")
        return False
    calls = _CURRENT.get("calls", [])
    st.setdefault("writing_v2_calls", []).extend(calls)
    new, n = apply_patch(body, out.read_text())
    if new is None:
        rec.setdefault("patches", []).append(dict(file=f"stages/{out.name}", applied=False, why=n, calls=calls, at=R.now()))
        R.save(d, st)
        R.say(f"      patch not applied ({n}) — rebuilding the pass instead")
        return False
    f.write_text(new)
    rec.setdefault("patches", []).append(dict(file=f"stages/{out.name}", applied=True, fixes=n, calls=calls, at=R.now()))
    rec["cost_usd"] = round((rec.get("cost_usd") or 0) + sum(c["cost_usd"] for c in calls), 4)
    R.save(d, st)
    split(d, st, p)
    R.say(f"      {n} fix(es) patched into the build — the same full audit reads it again")
    return True


def audit_rerun(d, st):
    """None when the audit ships; else (pass key, the audit's own words)."""
    rec = st["stages"].get("stage4e") or {}
    f = d / (rec.get("out") or "stages/4f-audit.md")
    if not f.is_file():
        return None
    body = f.read_text()
    m = re.search(r"VERDICT\W*\s*(SHIP|RE-RUN|STOP)([^\n]*)", body, re.I)
    if not m or m.group(1).upper() != "RE-RUN":
        return None
    tail = (m.group(2) + " " + body[m.end():m.end() + 300]).upper()
    for word in ("INJECTION", "HOOKS", "BUILD"):
        if word in tail:
            return RERUN[word], body
    n = re.search(r"\b(3|4[A-E])\b", tail)
    return (RERUN[n.group(1)] if n else "stage4v2b"), body


def unhandled_hand_audit(d, st):
    """A real consumed hand audit, including a legacy held result, can route once.

    Match both the emitted request and the consumed answer. The retry reservation
    records this identity; a held resume is not a new writing execution or a paid call.
    """
    import run as R
    rec = st.get("stages", {}).get("stage4e", {})
    if rec.get("model") != "session-hand" or rec.get("status") not in ("done", "held"):
        return None
    try:
        out = d / rec["out"]
        sent = d / rec["sent"]
        answer = Path(_HAND[0] or d / "hand") / out.name
        prompt = answer.with_suffix(".prompt.md")
        if sent.read_bytes() != prompt.read_bytes() or R.strip_lead_comment(answer.read_text()) != out.read_text():
            return None
        receipt = {"prompt_sha256": hashlib.sha256(sent.read_bytes()).hexdigest(),
                   "answer_sha256": hashlib.sha256(answer.read_bytes()).hexdigest(),
                   "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
    except (KeyError, OSError, UnicodeError):
        return None
    identity = hashlib.sha256((receipt["prompt_sha256"] + ":" + receipt["output_sha256"]).encode()).hexdigest()
    if any(h.get("identity") == identity for h in st.get("writing_retry_budget", {}).get("hand_audits", [])):
        return None
    return dict(receipt, identity=identity)


def _audit_notes_rule():
    import holds as H
    return H.notes_rule("audit")


def spent_audit_note(d, st, rec, words=None):
    """The audit's last findings, kept on the run as a note once its automatic repairs are spent."""
    import holds as H
    if words is None:
        f = Path(d) / (rec.get("out") or "stages/4f-audit.md")
        words = f.read_text() if f.is_file() else ""
    note = H.audit_note(words)
    rec.update(status="done", audit_spent=True, audit_note=note)
    rec.pop("error", None)
    notes = st.setdefault("writing_notes", {})
    notes.setdefault("audit", []).append(dict(note, at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
    st.pop("viewer_redo", None)
    return note


# ------------------------------------------------------------------ run

def run_writing(d, st, extras, brand=None, route=None, lane=None, allow_new_format=False):
    """Stages 3 → 5. True only for current accepted writing, never a held artifact."""
    import run as R
    d = Path(d)
    rt = (route or st.get("production_route") or "").lower()
    if rt and rt != "ai":
        # v2 has only the AI-lane brief (2026-10-19); a creator or founder run writes on v1:
        # the teardown's run.py --route <route> without --writing v2.
        R.say(f"  writing v2 is for the ai route only — this run is '{rt}'; it writes on v1 "
              f"(video-teardown run.py --route {rt}, no --writing v2)")
        return False
    st = apply_call(d, st)
    if not format_approved(st) and not allow_new_format:
        st.setdefault("stages", {})["stage3"] = dict(
            status="held", name="Injection",
            error=f"format {st.get('format_id')} is new to the bank — waiting for owner's call on the Swipes tab")
        R.save(d, st)
        R.say(f"  writing v2 HELD — format {st.get('format_id')} needs owner's call first")
        R.say(format_call_guidance())
        return False
    # the way out when every credential here is out of room: the run's own hand/ folder unless one is named, so
    # whoever runs the chain — any account, any tool — carries on (owner, 2026-10-23: "model and account agnostic")
    _HAND[0] = os.environ.pop("DAEMN_HAND_DIR", None) or _HAND[0] or str(d / "hand")
    R.claude = claude_v2                             # cache off, trimmed, cost logged
    # STAGE 2W, WINNER MATCH (owner, 2026-11-23): every swipe is matched with the brand's winners before any writing;
    # the ranking lands in winner-match.json and the writing on the winner lane waits for a person's pick.
    go, why = winner_match_step(d, st)
    R.save(d, st)
    if not go:
        st.setdefault("stages", {})["stage3"] = dict(status="held", name="Injection", error=why)
        R.save(d, st)
        R.say("  writing v2 HELD — " + why)
        return False
    if not (st.get("writing_lane") or {}).get("lane") or \
            (st["writing_lane"]["lane"] == "winner" and not st["writing_lane"].get("winner")):
        st.setdefault("stages", {})["stage3"] = dict(
            status="held", name="Injection",
            error="no writing lane: re-run with --writing-lane winner (the brand's winner, or --winner <run>) or --writing-lane swipe")
        R.save(d, st)
        R.say("  writing v2 HELD — pick a lane: --writing-lane winner (brand winner) or --writing-lane swipe (no winner yet)")
        return False
    try:
        args = who_args(d, st)
        selected = who_module().selection(st["brand"], args[1] if args else None, args[2] if args else None)
        if selected:
            st["selected_profile"] = selected
    except SystemExit as e:
        st.setdefault("stages", {})["stage3"] = dict(status="held", name="Injection", error=str(e))
        st["waiting_for"] = "strategist profile"
        R.save(d, st)
        R.say("  writing v2 HELD — " + str(e))
        return False
    if st.get("waiting_for") == "strategist profile":
        st.pop("waiting_for", None)
    keep_controls_preset(st, d)                      # one preset a run, by its awareness level, before any pass reads it
    extras = dict(extras or {})
    extras["declared_layers"] = declared_layers(st)
    extras.update(run_inputs(st))
    st["writing"] = "v2"
    aim = who_stamp(d, st)                           # who it is for and what it says, as data; a missing sub stops here
    if aim:
        st["aim"] = aim
        who_attach(d, st)
    st.pop("writing_error", None)
    R.save(d, st)
    passes = plan(brand or st["brand"], route or st.get("production_route") or "creator",
                  lane or st.get("triage_lane") or "")
    keys = [p["key"] for p in passes]
    register_pass_order(st, passes)
    st["writing_retry_budget"] = state.retry_budget(st, MAX_AUDIT_ROUNDS)
    R.save(d, st)
    budget = st["writing_retry_budget"]
    redo, rounds, i = set(budget.get("pending", [])), budget["used"], 0
    fully_checked = False
    rewrote = False          # a pass before the brief wrote something new on this run
    while i < len(passes):
        p = passes[i]
        _CURRENT.clear(); _CURRENT["key"] = p["key"]
        t0 = time.time()
        before = (st.get("stages") or {}).get(p["key"], {})
        before_status = before.get("status")
        if p["key"] == "stage4e" and not _audit_notes_rule() and before.get("status") == "held" and \
                str(before.get("error", "")).startswith("audit_retry_budget_exhausted"):
            state.save_result(d, st)                 # rolled back: the old hold
            return False
        if p["key"] == "stage4e" and (before.get("audit_spent") or (before.get("status") == "held" and str(
                before.get("error", "")).startswith("audit_retry_budget_exhausted"))):
            # REPAIRS SPENT: the line goes on to the brief with the audit's findings as notes (owner ruling,
            # 2026-11-20); a run held this way before the ruling resumes the same way, with no new audit call
            if not before.get("audit_spent"):
                spent_audit_note(d, st, before)
                R.save(d, st)
            i += 1
            continue
        if p["key"] == "stage5" and rewrote and before.get("status") in ("done", "held"):
            # THE BRIEF FOLLOWS ITS INPUTS (owner, 2026-11-20: small misses get the small fix, the run goes on): a pass
            # before it wrote something new on this run, so the kept brief is out of date and is written again
            redo.add("stage5")
        if p["key"] == "stage5" and before.get("status") in ("done", "held") and p["key"] not in redo:
            current = state.inspect_result(d, st)
            if not current["accepted"]:
                R.say("  5   Brief       existing artifact needs --revalidate; no writing call made")
                state.save_result(d, st)
                return False
        if p["key"] == "stage3":
            stop = matrix_start(d, st)                       # the creative matrix: no row, no start
            if stop:
                R.say("  matrix: " + stop)
                st.setdefault("stages", {}).setdefault(p["key"], {}).update(status="held", error="creative matrix: " + stop)
                R.save(d, st)
                return False
        try:
            ok = R.run_stage(d, st, p, extras, redo=p["key"] in redo)
        except RuntimeError as e:
            R.say(f"  {p['id']:<4} {p['name']} stopped — {str(e)[:200]}")
            ok = False
        st = json.loads((d / "run.json").read_text())      # run_stage saved its own copy
        rec = st["stages"].setdefault(p["key"], {})
        if _CURRENT.get("director"):     # stage 5d ran on this brief (director_after): its record rides on stage 5
            rec["director"] = _CURRENT["director"]
        budget = st["writing_retry_budget"]
        hand_audit = unhandled_hand_audit(d, st) if p["key"] == "stage4e" else None
        audit_ran = bool(_CURRENT.get("calls")) or hand_audit is not None
        if ok or (p["key"] == "stage4e" and audit_ran):
            budget["pending"] = [k for k in budget.get("pending", []) if k != p["key"]]
        if p["key"] == "stage5" and ok and before_status not in ("done", "held"):
            fully_checked = rec.get("status") == "done"
        calls = _CURRENT.get("calls", [])
        if calls and not p["key"].startswith("stage5"):
            rewrote = True
        if not calls:                    # a re-check of a held stage makes no call — keep its record
            calls = rec.get("calls") or []
            rec.setdefault("wall_seconds", round(time.time() - t0, 1))
        else:
            st.setdefault("writing_v2_calls", []).extend(calls)
        rec["cost_usd"] = round(sum(c["cost_usd"] for c in calls), 4)
        rec["api_seconds"] = round(sum(c["api_seconds"] for c in calls), 1)
        if _CURRENT.get("calls"):
            rec["wall_seconds"] = round(time.time() - t0, 1)
        rec["calls"] = calls
        if ok and p["key"] == "stage4i" and st.get("aim"):
            st["aim"] = who_stamp(d, st) or st["aim"]    # with the angle 4i chose
            who_attach(d, st)
        if ok and p["key"] == (st.get("viewer_redo") or {}).get("stage"):
            st.pop("viewer_redo", None)
        if ok and p["key"] == "stage3" and _CURRENT.get("calls"):
            note = matrix_written(d, st)                      # what was written, against its row: sent back once
            if note and not st.get("_matrix_remade"):
                st["_matrix_remade"] = True
                st["viewer_redo"] = {"stage": "stage3", "notes": "## THE CREATIVE MATRIX SENT THIS BACK\n\n" + note}
                R.save(d, st)
                R.say("      " + note.splitlines()[0])
                redo.add("stage3")
                continue
        R.save(d, st)
        redo.discard(p["key"])
        if ok and p.get("splits") and not _CURRENT.get("calls") and \
                all((st["stages"].get(x[1]) or {}).get("status") == "done" for x in p["splits"]):
            pass                          # already split on an earlier run; nothing new was written
        elif ok and p.get("splits"):
            try:
                split(d, st, p)
            except RuntimeError as e:
                R.say(f"      {str(e)[:200]}")
                hold = d / "HOOK-FORMAT.md"
                # a gate that sends the hooks back gets ONE remake with its own findings handed over
                if hold.is_file() and p["key"] == "stage4v2a" and not st.get("_v2_hook_remade"):
                    st = json.loads((d / "run.json").read_text())
                    st["_v2_hook_remade"] = True
                    st["viewer_redo"] = {"stage": p["key"], "notes":
                                         "## THE HOOK CHECK SENT THIS PASS BACK — fix every numbered finding, keep everything else\n\n"
                                         "Every variation prints its own `CARD Vn:` (words on screen in its first second) and its own "
                                         "`SCROLL Vn:` that starts with what HAPPENS in that take, not with a shared camera description "
                                         "(the camera is said once, in the FORMAT lines).\n\n" + hold.read_text()}
                    R.save(d, st)
                    R.say("      hook check sent the hooks back → one remake with its findings")
                    redo.add(p["key"])
                    continue
                return False
        if p["key"] == "stage4e":
            # A consumed session hand is a real audit too. Its exact request/answer identity
            # permits one recovery of a legacy held audit, never another retry on resume.
            again = learned_rerun(d, st, audit_rerun(d, st)) if audit_ran else None
            if again and budget["used"] >= budget["limit"] and not _audit_notes_rule():
                rec["status"] = "held"                  # rolled back (holds.json lanes.audit): the old hold
                rec["error"] = "audit_retry_budget_exhausted: automatic audit repairs are spent for this run"
                R.save(d, st)
                state.save_result(d, st)
                return False
            if again and budget["used"] >= budget["limit"]:
                # REPAIRS SPENT, THE BRIEF STILL GETS WRITTEN (owner ruling, 2026-11-20): the audit's findings ride on
                # the run as notes; money and law are held later, on the finished brief, by the claims check.
                spent_audit_note(d, st, rec, again[1])
                R.save(d, st)
                R.say("      audit repairs are spent — the brief is written with the audit's findings as notes")
                i += 1
                continue
            if again:
                target, words = again
                budget["used"] += 1
                rounds = budget["used"]
                budget["pending"] = keys[keys.index(target):keys.index("stage4e") + 1]
                budget.setdefault("history", []).append({"round": rounds, "target": target, "at": R.now()})
                if hand_audit is not None:
                    budget.setdefault("hand_audits", []).append(
                        dict(hand_audit, round=rounds, target=target, at=R.now()))
                st["viewer_redo"] = {"stage": target, "notes":
                                     "## THE AUDIT SENT THIS PASS BACK — keep everything else\n\n" + words.strip()}
                # Reserve before work: a crash/resume cannot silently grant another budget.
                R.save(d, st)
                if target == "stage4v2b":
                    R.say(f"      audit says RE-RUN → patching {target} (round {rounds}), then the same audit again")
                    try:
                        patched = patch_build(d, st, passes[keys.index(target)], words, extras)
                    except HandPromptMismatch as e:
                        st["writing_error"] = str(e)
                        R.save(d, st)
                        state.save_result(d, st)
                        return False
                    except Exception as e:      # a patch that breaks never costs the run: rebuild instead
                        R.say(f"      the patch could not be applied ({type(e).__name__}: {str(e)[:120]}) — rebuilding")
                        patched = False
                    if patched:
                        st = json.loads((d / "run.json").read_text())
                        st["stages"].pop("stage4e", None)
                        st["writing_retry_budget"]["pending"] = ["stage4e"]
                        R.save(d, st)
                        redo.add("stage4e")
                        i = keys.index("stage4e")
                        continue
                R.say(f"      audit says RE-RUN → re-running {target} (round {rounds}), then auditing again")
                st["viewer_redo"] = {"stage": target, "notes":
                                     "## THE AUDIT SENT THIS PASS BACK — fix exactly what it names, keep everything else\n\n"
                                     + words.strip()}
                st["stages"].pop("stage4e", None)
                R.save(d, st)
                redo |= set(keys[keys.index(target):keys.index("stage4e") + 1])
                i = keys.index(target)
                continue
            if not ok:
                return False
        elif not ok:
            state.save_result(d, st)
            return False
        i += 1
    st["writing_v2_total"] = dict(
        cost_usd=round(sum(c["cost_usd"] for c in st.get("writing_v2_calls", [])), 4),
        api_seconds=round(sum(c["api_seconds"] for c in st.get("writing_v2_calls", [])), 1),
        calls=len(st.get("writing_v2_calls", [])), audit_rounds=rounds)
    R.save(d, st)
    if apply_owner_check(d) is False:                 # the owner's locked words, line by line (2026-10-23)
        R.say("      the owner's locked words are not all in the brief — HELD, named in run.json owner_words_check")
        return False
    st = json.loads((d / "run.json").read_text())
    if fully_checked:
        state.record_acceptance(d, st)
        R.save(d, st)
    return state.save_result(d, st)["accepted"]


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Video writing v2 on one run folder.")
    ap.add_argument("run_dir")
    ap.add_argument("--revalidate", action="store_true",
                    help="check existing brief bytes once; no writing passes, repairs or source changes")
    ap.add_argument("--allow-new-format", action="store_true",
                    help="write on a 'new:' format owner has not ruled on yet (test runs only)")
    ap.add_argument("--sandbox", action="store_true",
                    help="a test copy of a run: the swipe library shelf goes inside the copy, the viewer check is off")
    ap.add_argument("--owner-script", dest="owner_script",
                    help="the owner's locked script (markdown with a LINES table): every pass carries its lines verbatim")
    ap.add_argument("--story", help="our own story (a concept file): the piece keeps the swipe's format and "
                                    "structure and tells this story instead of the swipe's")
    ap.add_argument("--format", dest="format_id", help="the format the piece is written in (a format bank id)")
    ap.add_argument("--ask", help="the ask this ad was ordered with: an ask.json path, or an ask's name under "
                                  "runs/creative-strategist/<brand>/; its offer lines and moment win over the offer bank")
    ap.add_argument("--preset", help="the story preset the piece is written in (an id from creative-controls "
                                     "story_presets.json), or 'auto' to pick one from the run's format and avatar")
    ap.add_argument("--dry", action="store_true",
                    help="build the first pass's prompt with every input and block, file it, call no model")
    a = ap.parse_args()
    d = Path(a.run_dir).resolve()
    if a.revalidate:
        if any((a.ask, a.story, a.format_id, a.owner_script, a.sandbox, a.allow_new_format, a.preset, a.dry)):
            ap.error("--revalidate checks the existing inputs; do not combine it with input-changing or bypass flags")
        from writing_revalidate import revalidate
        result = revalidate(d)
        print(json.dumps({**result, "ok": result["accepted"]}, indent=1))
        return result["accepted"]
    if a.ask:
        name_ask(d, a.ask)
    if a.preset:
        rec = name_preset(d, a.preset)
        print(f"story preset: {rec['id']} ({rec['picked_by']}: {rec['why']})")
    if a.dry:
        _DRY[0] = True
    if a.story:
        lock_story(d, a.story)
    if a.format_id:
        set_format(d, a.format_id)
    if a.owner_script:
        lock_owner_script(d, a.owner_script)
    st = json.loads((d / "run.json").read_text())
    if a.sandbox:
        import run as R
        R.library_home = lambda *_a, **_k: d / "_library"     # never the real swipe's Drive shelf
        os.environ["QC_VIEWER"] = "0"
    dec = st.get("declared_audience") or {}
    extras = {"video_count": "1", "brand_name": st["brand"].replace("-", " ").title(),
              "product": st.get("product") or "", "declared_avatar": dec.get("avatar") or "",
              "declared_sub": dec.get("sub") or "", "post_url": st.get("post_url") or "",
              "declared_audience": ""}
    try:
        ok = run_writing(d, st, extras, allow_new_format=a.allow_new_format)
    except Exception as exc:
        st = json.loads((d / "run.json").read_text())
        st["writing_error"] = {"error_type": type(exc).__name__,
                               "http_status": getattr(exc, "code", None),
                               "detail": "Writing stopped before acceptance; inspect the stage records."}
        (d / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
        ok = False
    if _DRY[0]:
        filed = sorted((d / "prompts").glob("*.md"), key=lambda f: f.stat().st_mtime)
        print("dry run — no model called. Prompt as it would be sent: %s" % (filed[-1] if filed else "none filed"))
        return bool(filed)
    st = json.loads((d / "run.json").read_text())
    notes = preset_check(d)
    if notes:
        print("story preset notes: " + "; ".join(notes))
    stock_moment_check(d, st)
    passed = apply_owner_check(d)
    if passed is not None:
        st = json.loads((d / "run.json").read_text())
        missed = st["owner_words_check"]["missing"]
        ok = ok and passed
        print(f"owner's words: {'all ' + str((st.get('owner_script') or {}).get('lines')) + ' lines in the brief' if not missed else str(len(missed)) + ' missing — brief HELD'}")
    st = json.loads((d / "run.json").read_text())
    result = state.save_result(d, st)
    ok = bool(ok and result["accepted"])
    print(json.dumps({**result, "ok": ok, "total": st.get("writing_v2_total"),
                      "stages": {k: {x: v.get(x) for x in ("status", "cost_usd", "api_seconds", "wall_seconds")}
                                 for k, v in st["stages"].items() if k in [p[0] for p in PASSES]}}, indent=1))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)    # a stopped writing run exits non-zero, so a job never files it as done
