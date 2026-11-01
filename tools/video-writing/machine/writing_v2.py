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

Prompts: tools/video-writing/prompts/v2/ (not a v1 prompt home, so v1
never picks them up).

Run:  python3 tools/video-writing/machine/run.py <teardown run> [--allow-new-format]
  or: python3 writing_v2.py <run dir> [--allow-new-format]
  or: video-teardown run.py ... --writing v2   (the teardown hands its writing stages to this file)
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The chain engine (prompt filling, model calls, the run record) is the teardown's and is
# shared; writing reads it from there by path (video-writing CLAUDE.md, "What it leans on").
TD = HERE.parents[1] / "video-teardown" / "machine"
sys.path.insert(0, str(TD))
import chain as C   # noqa: E402

V2 = C.WRITING_PROMPTS / "v2"
WS = C.WS

# (pass key, display id, file id, name, prompt, [(marker, v1 key, v1 file id, v1 name)])
PASSES = [
    ("stage3", "3", "3", "Injection", "stage3-injection-v8-damon.md", None),
    ("stage4v2a", "4ab", "4ab", "Reading Hooks", "stage4v2a-readhooks-v6-damon.md",
     [("READING", "stage4r", "4a", "Reading"), ("HOOKS", "stage4b", "4b", "Hooks")]),
    ("stage4v2b", "4cde", "4cde", "Placement Expansion Close", "stage4v2b-build-v6-damon.md",
     [("PLACEMENT", "stage4a", "4c", "Placement"), ("EXPANSION", "stage4c", "4d", "Expansion"),
      ("CLOSE", "stage4d", "4e", "Close")]),
    ("stage4e", "4f", "4f", "Audit", "stage4e-audit-v8-damon.md", None),   # v5: verify row 11, no NO ENTRY in the rung map
    ("stage4g", "4g", "4g", "Spice", "stage4g-spice-v8-damon.md", None),   # v4: V23, organic closes on the turn + the ask
    # the brief as a shooting script (2026-10-21, video-system sync W1-W25): shots, per-line reads, the lane
    # (v4, verify row 22: its history no longer says a scene carries voice_settings)
    ("stage5", "5", "5", "Brief", "stage5-ai-brief-v10-damon.md", None),   # v9 (2026-10-28): brand-free, no rule changed · v8 (2026-10-28): the demo stays on its object; props make sense   # v5: V23, the organic end card is the ask only
]
# the run-time inputs every pass may ask for, filled by run_writing (never from the config)
RUN_INPUTS = ("declared_layers", "ask_lane", "video_spice", "realism_index", "creative_controls", "emotion_video_lines",
              "controls_target")
V1_WRITING = ("stage3", "stage4r", "stage4m", "stage4b", "stage4a", "stage4c", "stage4d",
              "stage4e", "stage4g", "stage5")
# what the audit may name, -> the pass that re-runs
RERUN = {"INJECTION": "stage3", "HOOKS": "stage4v2a", "BUILD": "stage4v2b",
         "3": "stage3", "4A": "stage4v2a", "4B": "stage4v2a", "4C": "stage4v2b",
         "4D": "stage4v2b", "4E": "stage4v2b"}
MAX_AUDIT_ROUNDS = 2

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

def _env():
    import run as R
    e = R._clean_env()
    e["DISABLE_PROMPT_CACHING"] = "1"      # measured 2026-10-18: same prompt $0.84 -> $0.52
    return e


def claude_v2(prompt_text, out, model_name=None):
    """v1's claude() with the cache off, the inputs trimmed, and the cost logged.
    Writes on the machine; only when that login is at its limit does it fall to the session hand (19 Oct)."""
    import run as R
    d = out.parent.parent
    st = json.loads((d / "run.json").read_text())
    key = _CURRENT.get("key") or ""
    prompt_text, trims = slim(prompt_text, key, d, st)
    prompt_text = owner_block(d, st) + prompt_text       # THE OWNER'S LOCKED SCRIPT (2026-10-23), when the run has one
    prompt_text = story_block(d, st) + prompt_text       # OUR STORY on the swipe's format (2026-10-28), when it has one
    sent = d / "prompts" / out.name
    if sent.parent.is_dir():
        sent.write_text(prompt_text)          # the prompt on file is the prompt that was sent
    model = R._cli_model(model_name or "opus")
    limit = int(os.environ.get("VT_CLAUDE_TIMEOUT", "1500"))
    hand = _HAND[0]
    if hand and (Path(hand) / out.name).is_file():          # a session already wrote this stage: use it, no CLI call
        out.write_text((Path(hand) / out.name).read_text())
        return "session-hand"
    kit = next(str(p / "components" / "run-kit") for p in Path(__file__).resolve().parents
               if (p / "components" / "run-kit").is_dir())
    if kit not in sys.path:
        sys.path.append(kit)   # appended, never ahead of this machine
    from run_kit.claude_flags import effort_args   # LD-73 (explicit effort)
    t0 = time.time()
    for attempt in (1, 2):
        try:
            # NO ACCOUNT IS WIRED IN (the owner, 2026-10-23): started through run_kit's
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
        (hd / (out.stem + ".prompt.md")).write_text(prompt_text)
        raise RuntimeError(f"waiting for the session hand: {hd / (out.stem + '.prompt.md')}")
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
    return model


# ------------------------------------------------------------------ the owner's locked script (2026-10-23)
# the owner, 2026-10-23, after a hand-typed brief broke the pastor barber body: the chain had no door for a script HE wrote
# ("build the door"). The script goes in as a file (--owner-script); every writing pass is handed it as fixed words
# — carry every spoken line verbatim, build everything else (structure, scenes, frames, beats, B-roll, the brief)
# around it — and after the brief the words are checked line by line: a line missing or changed holds the brief,
# named. The script file lives in the run folder (owner-script.md) and run.json records who locked it and its hash.

OWNER_FILE = "owner-script.md"


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
# the owner, 2026-10-28, on the first song ad through the new chain: "we don't need a teardown just the writing" — the
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


def lock_story(d, src, by="the owner"):
    import hashlib
    from datetime import datetime, timezone
    d = Path(d)
    text = Path(src).read_text()
    (d / STORY_FILE).write_text(text)
    st = json.loads((d / "run.json").read_text())
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


def lock_owner_script(d, src, by="the owner"):
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
    lines = [f"- **FORMAT:** `{fid}`" + (f" — {row.get('name')}: {row.get('what')}" if row else
                                         (" — a format new to the bank, approved for this run" if fid.startswith("new:") else "")),
             f"- **STYLE:** `{lay.get('style') or st.get('style_id') or 'unknown'}`",
             f"- **STRUCTURE:** {lay.get('structure') or doc.get('framework') or 'as the doctrine read gives it'}",
             f"- **HOW IT'S MADE:** {lay.get('made') or st.get('production_route') or 'creator'}"]
    beats = (row.get("extra") or {}).get("beats") if row else None
    if beats:
        lines.append(f"- **THE FORMAT'S BEATS:** {beats}")
    pb, where = format_playbook(fid)
    if pb:
        lines.append(f"- **THE FORMAT'S PLAYBOOK** ({where}) — how this format is made, stage by stage; write "
                     f"inside it, and where the swipe itself differs, the swipe wins:\n\n{pb.strip()}")
    return "\n".join(lines)


PLAYBOOKS = WS / "tools/video-production/formats/playbooks"


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
        var = next((v for v in j.get("variants") or [] if isinstance(v, dict) and v.get("id") == fid), None)
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
            "controls_target": controls_target(st)}


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
    """The story layer (2026-10-28, the owner: "amplify creative storytelling abilities, conversion, amplification,
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


def controls_target(st):
    """The VIDEO dials' levels to aim for: every video dial's default, the preset on top, the saved brand levels, the
    never-sterile floor (creative_controls.target). One line per dial; the brief turns them into face, gestures, camera, timing."""
    try:
        return _controls().target_md("maxed", (st or {}).get("brand"), "video")
    except Exception as e:   # noqa: BLE001 — an unreadable input is said, not fatal
        return f"[UNFILLED] — the video dial levels could not be read ({str(e)[:100]})"


def video_spice():
    """VIDEO-SPICE.md, whole — the seven layers and the levels (V9)."""
    return _read(WS / "tools/video-production/VIDEO-SPICE.md").strip() or "[UNFILLED] — VIDEO-SPICE.md not found"


def realism_rows(st):
    """The realism index's WRITING-stage rows (stage `writing`, or `writing` in `also`), this run's format first.
    The index is video-production's definition file (spice/realism-index.json); it is read, never written."""
    try:
        j = json.loads(_read(WS / "tools/video-production/spice/realism-index.json") or "{}")
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
    """the owner's call on a new format, applied before writing (review, 19 Oct): "Same as X" (fold) writes it as
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


def format_approved(st):
    """A format the bank does not have ('new:<name>') stops for the owner's call. Read through the
    teardown's one call reader (layers.call_for, 2026-10-19): it used to look for a shape Outlier
    never writes, so a call made on the Swipes tab never released the run."""
    import layers as L
    if any(not L.call_for(p) for p in (st.get("layers_pending") or [])):
        return False                      # a new layer still waits for the owner's call
    fid = (st.get("layers") or {}).get("format") or st.get("format_id") or ""
    if not fid.startswith("new:"):
        return True
    return L.call_for(fid) is not None


def plan(brand, route, lane):
    """v2's stage dicts, with v1's bindings for the same work."""
    v1 = {s["key"]: s for s in C.stages(brand, "", route, lane)}
    pool = C.known_sources()
    out = []
    for key, sid, fid, name, prompt, splits in PASSES:
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
        vars_ = {k: v for k, v in vars_.items() if k in asks}
        if route and "production_route" in vars_:
            vars_["production_route"] = "=" + ("AI" if route.lower() == "ai" else route.lower())
        base = v1.get(key) or {}
        out.append(dict(key=key, id=sid, file_id=fid, name=name, group="Writing v2", blurb="",
                        prompt=str(p), version=2, engine="claude", vars=vars_,
                        per_run=sorted(C.PER_RUN & set(vars_)), role="stage", search=False,
                        model="opus", splits=splits, config_prompt=base.get("config_prompt")))
    return out


# ------------------------------------------------------------------ split

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
            matrix, problems = hook_matrix.from_text((d / out_name).read_text(), st.get("brand"))
            if problems:
                (d / "HOOK-FORMAT.md").write_text("# Hook matrix needs repair\n\n" + "\n".join(problems))
                st["stages"][k1]["status"] = "error"
                st["stages"][k1]["error"] = "; ".join(problems)
                R.save(d, st)
                raise RuntimeError("Hook creative controls / visual format: " + "; ".join(problems))
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
PATCH_PROMPT = "stage4v2b-patch-v1-damon.md"
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


# ------------------------------------------------------------------ run

def run_writing(d, st, extras, brand=None, route=None, lane=None, allow_new_format=False):
    """Stages 3 → 5, v2. Returns True when the brief is written (done or held by
    its own gates, exactly like v1), False when the writing stopped."""
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
            error=f"format {st.get('format_id')} is new to the bank — waiting for the owner's call on the Swipes tab")
        R.save(d, st)
        R.say(f"  writing v2 HELD — format {st.get('format_id')} needs the owner's call first")
        return False
    # the way out when every credential here is out of room: the run's own hand/ folder unless one is named, so
    # whoever runs the chain — any account, any tool — carries on (the owner, 2026-10-23: "model and account agnostic")
    _HAND[0] = os.environ.pop("DAEMN_HAND_DIR", None) or _HAND[0] or str(d / "hand")
    R.claude = claude_v2                             # cache off, trimmed, cost logged
    extras = dict(extras or {})
    extras["declared_layers"] = declared_layers(st)
    extras.update(run_inputs(st))
    st["writing"] = "v2"
    R.save(d, st)
    passes = plan(brand or st["brand"], route or st.get("production_route") or "creator",
                  lane or st.get("triage_lane") or "")
    keys = [p["key"] for p in passes]
    redo, rounds, i = set(), 0, 0
    while i < len(passes):
        p = passes[i]
        _CURRENT.clear(); _CURRENT["key"] = p["key"]
        t0 = time.time()
        try:
            ok = R.run_stage(d, st, p, extras, redo=p["key"] in redo)
        except RuntimeError as e:
            R.say(f"  {p['id']:<4} {p['name']} stopped — {str(e)[:200]}")
            ok = False
        st = json.loads((d / "run.json").read_text())      # run_stage saved its own copy
        rec = st["stages"].setdefault(p["key"], {})
        calls = _CURRENT.get("calls", [])
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
        if p["key"] == (st.get("viewer_redo") or {}).get("stage"):
            st.pop("viewer_redo", None)
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
            # only an audit that actually ran this round sends work back; a held audit re-checked
            # against the owner's approvals does not
            again = audit_rerun(d, st) if _CURRENT.get("calls") else None
            if again and rounds < MAX_AUDIT_ROUNDS:
                target, words = again
                rounds += 1
                if target == "stage4v2b":
                    R.say(f"      audit says RE-RUN → patching {target} (round {rounds}), then the same audit again")
                    try:
                        patched = patch_build(d, st, passes[keys.index(target)], words, extras)
                    except Exception as e:      # a patch that breaks never costs the run: rebuild instead
                        R.say(f"      the patch could not be applied ({type(e).__name__}: {str(e)[:120]}) — rebuilding")
                        patched = False
                    if patched:
                        st = json.loads((d / "run.json").read_text())
                        st["stages"].pop("stage4e", None)
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
            return p["key"] == "stage5" and st["stages"].get("stage5", {}).get("status") == "held"
        i += 1
    st["writing_v2_total"] = dict(
        cost_usd=round(sum(c["cost_usd"] for c in st.get("writing_v2_calls", [])), 4),
        api_seconds=round(sum(c["api_seconds"] for c in st.get("writing_v2_calls", [])), 1),
        calls=len(st.get("writing_v2_calls", [])), audit_rounds=rounds)
    R.save(d, st)
    if apply_owner_check(d) is False:                 # the owner's locked words, line by line (2026-10-23)
        R.say("      the owner's locked words are not all in the brief — HELD, named in run.json owner_words_check")
        return False
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Video writing v2 on one run folder.")
    ap.add_argument("run_dir")
    ap.add_argument("--allow-new-format", action="store_true",
                    help="write on a 'new:' format the owner has not ruled on yet (test runs only)")
    ap.add_argument("--sandbox", action="store_true",
                    help="a test copy of a run: the swipe library shelf goes inside the copy, the viewer check is off")
    ap.add_argument("--owner-script", dest="owner_script",
                    help="the owner's locked script (markdown with a LINES table): every pass carries its lines verbatim")
    ap.add_argument("--story", help="our own story (a concept file): the piece keeps the swipe's format and "
                                    "structure and tells this story instead of the swipe's")
    ap.add_argument("--format", dest="format_id", help="the format the piece is written in (a format bank id)")
    a = ap.parse_args()
    d = Path(a.run_dir).resolve()
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
    ok = run_writing(d, st, extras,
                     allow_new_format=a.allow_new_format)
    st = json.loads((d / "run.json").read_text())
    passed = apply_owner_check(d)
    if passed is not None:
        st = json.loads((d / "run.json").read_text())
        missed = st["owner_words_check"]["missing"]
        ok = ok and passed
        print(f"owner's words: {'all ' + str((st.get('owner_script') or {}).get('lines')) + ' lines in the brief' if not missed else str(len(missed)) + ' missing — brief HELD'}")
    print(json.dumps({"ok": ok, "total": st.get("writing_v2_total"),
                      "stages": {k: {x: v.get(x) for x in ("status", "cost_usd", "api_seconds", "wall_seconds")}
                                 for k, v in st["stages"].items() if k in [p[0] for p in PASSES]}}, indent=1))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)    # a stopped writing run exits non-zero, so a job never files it as done
