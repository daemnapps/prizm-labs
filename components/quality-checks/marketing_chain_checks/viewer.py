"""THE VIEWER CHECK — the last check after the writing stages, in every chain
(the owner, 2026-10-02: "slide this into the chains and lets ride it"; the design:
VIEWER-CHECK.md).

From Andrei Lunev's "Toilet Mike": the ad is judged by someone who is not a
marketer, scrolling, and the maker never grades its own work. Ours drops the ad
into its avatar's REAL feed (an avatar feed: `<feeds>/<brand>--<avatar>/items.json`,
see FEEDS below) among 9 real posts and lets 5 fresh viewers scroll it. The viewers only react; this file scores, in
code, against the real posts beside it — so the viewer cannot be gamed into
passing an ad ("looks real" is never scored).

    from marketing_chain_checks import viewer
    r = viewer.check(run_dir, brand, avatar, brief_path, kind="video", sub=None, round_n=1)
    r["passed"], r["fix_at"], r["notes"]       # fix_at: openings|middle|giveaway|close|audience

Each chain maps fix_at to its own writing step. Files every round to
<run>/viewer-check/r<N>/ (what each viewer was sent, their answers, VERDICT.md)
and to <run>/qc-log/. Off: QC_VIEWER=0. Nothing here names a brand.
"""
from __future__ import annotations

import json, os, random, re, statistics, sys, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
sys.path.append(str(COMP.parent / "run-kit"))     # appended, never ahead of the caller's own modules
from run_kit import paths as RK                   # noqa: E402  the one workspace locator (triage page 12)
try:                                             # the brand-folder map, where a workspace has one
    if "brandpath" not in sys.modules:
        sys.path.append(str(COMP.parent / "brandpath"))
    import brandpath as BP                        # noqa: E402
except ImportError:
    BP = None                                     # brands/<brand>/<folder>/… as laid out in brands/_TEMPLATE
WS = RK.repo(HERE)
PROMPTS = COMP / "prompts"
RECORDS = Path(os.environ.get("VIEWER_RECORDS") or (COMP / "records"))   # your data, never shipped (.gitignore)
CARDS = RECORDS / "viewer-cards"
# Each avatar's real feed: <FEEDS>/<brand>--<avatar>/items.json — a list of real
# organic posts ({author, caption, sift: {keep, what}}) pulled from accounts that
# avatar follows. Set VIEWER_FEEDS to wherever yours live.
FEEDS = Path(os.environ.get("VIEWER_FEEDS") or (WS / "components" / "swipe-organic" / "records" / "avatar-feeds"))
ENGINE = os.environ.get("QC_VIEWER_ENGINE", "claude")   # claude (default) · gemini (Gemini, then OpenAI) — only on purpose
MODEL = os.environ.get("QC_VIEWER_MODEL", "gemini-3-flash-preview")          # the viewers (engine=gemini only)
CUT_MODEL = os.environ.get("QC_VIEWER_CUT_MODEL", "gemini-3.1-pro-preview")   # brief → what a viewer sees
BASE = "https://generativelanguage.googleapis.com/v1beta/models"
N_VIEWERS, N_POSTS = 5, 9      # 3 swung pass/fail on an unchanged brief (2026-10-02)
WHENS = ["11:40pm on a weeknight, in bed, should be asleep",
         "4:15pm, on the way home",
         "1:10am on a Saturday, can't sleep",
         "7:20am, still in bed before getting up",
         "12:30pm, on a break, killing ten minutes"]
OFF_WORDS = ("not for me", "didn't get it", "didnt get it", "who is this for")


def newest(stem: str) -> Path:
    """The highest -vN-damon.md wins (the prompt-library convention)."""
    got = sorted(PROMPTS.glob(f"{stem}-v*-damon.md"),
                 key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    if not got:
        raise FileNotFoundError(f"no {stem} prompt in {PROMPTS}")
    return got[-1]



def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod


def _key():
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if k:
        return k
    return _shared_keys().lookup("GEMINI_API_KEY")


def _json(t: str) -> dict:
    """The answer's JSON, even with text or a second object after it."""
    t = t.strip()
    try:
        return json.loads(t)
    except ValueError:
        i = t.find("{")
        if i < 0:
            raise
        return json.JSONDecoder().raw_decode(t[i:])[0]


_CLAUDE_OK = [None]   # None = untried · False = not signed in this run


def _claude_cli(text: str, as_json: bool):
    """Claude on your own plan, headless (`claude -p`, no tools, no API key).
    Returns None when it isn't available, so the call falls through to Gemini,
    then OpenAI. Off: QC_VIEWER_CLAUDE=0."""
    if _CLAUDE_OK[0] is False or os.environ.get("QC_VIEWER_CLAUDE", "1") == "0" or "unittest" in sys.modules:
        return None
    import shutil, subprocess
    if not shutil.which("claude"):
        _CLAUDE_OK[0] = False
        return None
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    try:
        r = subprocess.run(["claude", "-p", "--allowed-tools", "", "--output-format", "json"],
                           input=text + ("\n\n(Answer with the JSON only.)" if as_json else ""),
                           capture_output=True, text=True, env=env, timeout=900, cwd="/tmp")
        d = json.loads(r.stdout or "{}")
    except Exception:
        return None
    if d.get("is_error") or not d.get("result"):
        if re.search(r"authenticat|oauth|log ?in|limit", str(d.get("result", "")), re.I):
            _CLAUDE_OK[0] = False      # not signed in or capped: don't try again this run
        return None
    _CLAUDE_OK[0] = True
    USED.add("claude")
    t = str(d["result"])
    return _json(t) if as_json else t.strip()


def _openai(text: str, as_json: bool, model: str):
    body = {"model": model, "messages": [{"role": "user", "content": text}]}
    if as_json:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {_shared_keys().lookup('OPENAI_API_KEY')}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        t = json.loads(r.read())["choices"][0]["message"]["content"] or ""
    return _json(t) if as_json else t.strip()


FALLBACK = {"strong": os.environ.get("QC_VIEWER_FALLBACK_STRONG", "gpt-5.5"),
            "fast": os.environ.get("QC_VIEWER_FALLBACK_FAST", "gpt-5.4-mini")}
USED = set()       # which models answered this check — written into the verdict


import threading
_HAND_LOCK = threading.Lock()
HAND_DEFAULT = [None]   # set by run_loop to <run>/hand, so the session finds the questions beside the brief


def _hand(text: str, as_json: bool, image: str | None = None):
    """THE SESSION HAND (the owner, 2026-10-03: "you can use claude for this anyways
    we're analyzing text"). With VIEWER_HAND_DIR set, every model call is left
    as a numbered prompt file and answered by Claude in the session — fresh
    helpers that see only that one prompt — instead of an API key. The run
    waits for <n>.answer.md beside it; every check in this file still applies."""
    import time
    d = Path(os.environ.get("VIEWER_HAND_DIR") or HAND_DEFAULT[0] or (WS / "runs" / "viewer-check" / "_hand")); d.mkdir(parents=True, exist_ok=True)
    title = re.sub(r"[^a-z0-9]+", "-", (text.strip().splitlines() or ["prompt"])[0].lower()).strip("-")[:40]
    with _HAND_LOCK:
        n = len(list(d.glob("*.prompt.md"))) + 1
        pf = d / f"{n:03d}-{title}.prompt.md"
        pf.write_text("")
    af = pf.with_name(pf.name.replace(".prompt.md", ".answer.md"))
    body = text + (f"\n\n--- THE IMAGE ---\nRead this image file and look at it: {image}\n" if image else "")
    body += ("\n\n(Answer with the JSON only.)" if as_json else "")
    pf.write_text(body)
    limit = time.time() + int(os.environ.get("VIEWER_HAND_TIMEOUT", "3600"))
    while time.time() < limit:
        if af.exists() and af.stat().st_size > 0:
            time.sleep(1)
            t = af.read_text()
            USED.add("claude (session)")
            return _json(t) if as_json else t.strip()
        time.sleep(3)
    raise TimeoutError(f"no answer written for {pf.name}")


def ask(text: str, temperature: float = 0.0, as_json: bool = True, caller=None, model: str | None = None):
    """Gemini first. Gemini refuses some brands' profiles outright
    (PROHIBITED_CONTENT on one brand's, 2026-10-02) — then OpenAI answers, so a
    brand is never held for the model's own rule rather than the ad."""
    if caller:
        return caller(text, temperature, as_json)
    if os.environ.get("VIEWER_HAND_DIR"):
        return _hand(text, as_json)
    got = _claude_cli(text, as_json)       # the owner, 2026-10-03: "use claude for this … we're analyzing text"
    if got is not None:
        return got
    if ENGINE == "claude":
        # Claude only (the owner, 2026-10-03: "we can just use claude for this").
        # Headless Claude isn't signed in, so the question is left for the Claude
        # session running this brief to answer — never another company's model.
        return _hand(text, as_json)
    m = model or MODEL
    cfg = {"temperature": temperature}
    if as_json:
        cfg["responseMimeType"] = "application/json"
    body = {"contents": [{"parts": [{"text": text}]}], "generationConfig": cfg}
    req = urllib.request.Request(f"{BASE}/{m}:generateContent?key={_key()}",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (402, 429, 500, 503):           # out of credit or down: answer elsewhere, never stall a brief
            fb = FALLBACK["strong" if m == CUT_MODEL else "fast"]
            USED.add(f"{fb} (Gemini {e.code})")
            return _openai(text, as_json, fb)
        raise
    cands = data.get("candidates") or []
    parts = (cands[0].get("content") or {}).get("parts") if cands else None
    if not parts:
        fb = FALLBACK["strong" if m == CUT_MODEL else "fast"]
        USED.add(f"{fb} (Gemini refused: {(data.get('promptFeedback') or {}).get('blockReason') or (cands[0].get('finishReason') if cands else 'empty')})")
        return _openai(text, as_json, fb)
    USED.add(m)
    t = "".join(p.get("text", "") for p in parts)
    return _json(t) if as_json else t.strip()


# ── the pieces ─────────────────────────────────────────────────────────────

def _brand(brand: str, key: str, *rest: str) -> Path:
    """A brand's file or folder through brandpath, inside the workspace WS
    names — so a folder rename moves no code here."""
    if BP is not None:
        return BP.brand_path(brand, key, *rest, root=WS / "brands")
    return WS.joinpath("brands", brand, key, *rest)


def profile_path(brand: str, avatar: str, sub: str | None = None) -> Path | None:
    core = _brand(brand, "core-avatars", avatar)
    if sub:
        hits = sorted((core / "sub-avatars").glob(f"sub-*-{sub}.md")) + sorted((core / "sub-avatars").glob(f"{sub}.md"))
        if hits:
            return hits[0]
    p = core / "profile.md"
    return p if p.exists() else None


def card(brand: str, avatar: str, sub: str | None = None, caller=None) -> tuple[str, Path]:
    """The viewer card, cached per profile version (brands/ is read-only to
    machines, so the cache lives here). A changed profile writes a fresh card."""
    prof = profile_path(brand, avatar, sub)
    if not prof:
        raise FileNotFoundError(f"no profile for {brand}/{avatar}" + (f"/{sub}" if sub else ""))
    text = prof.read_text()
    if sub:                                 # a sub-avatar reads with its core behind it
        core = profile_path(brand, avatar)
        if core and core != prof:
            text = core.read_text()[:20000] + "\n\n--- THIS SUB-GROUP ---\n" + text
    import hashlib
    h = hashlib.md5(text.encode()).hexdigest()[:10]
    name = f"{brand}--{avatar}" + (f"--{sub}" if sub else "")
    CARDS.mkdir(parents=True, exist_ok=True)
    cached = CARDS / f"{name}.md"
    if cached.exists() and f"<!-- profile {h} -->" in cached.read_text():
        return cached.read_text().split("-->", 1)[1].strip(), cached
    tpl = newest("viewer-card").read_text()
    got = ask(tpl.replace("{brand}", brand).replace("{avatar}", sub or avatar)
                 .replace("{profile}", text[:40000]), as_json=False, caller=caller, model=CUT_MODEL)
    cached.write_text(f"<!-- profile {h} -->\n{got.strip()}\n")
    return got.strip(), cached


def feed_dir(brand: str, avatar: str, sub: str | None = None) -> Path | None:
    subs = [sub, re.sub(r"^sub-\d+-", "", sub)] if sub else []
    for n in subs + [avatar]:
        p = FEEDS / f"{brand}--{n}"
        if (p / "items.json").exists():
            return p
    return None


def feed_posts(folder: Path, seed: int, n: int = N_POSTS) -> list[dict]:
    raw = json.loads((folder / "items.json").read_text())
    items = raw.get("items", raw) if isinstance(raw, dict) else raw
    items = list(items.values()) if isinstance(items, dict) else items
    kept = [x for x in items if (x.get("sift") or {}).get("keep") and x.get("status") != "retired"]
    pool = kept if len(kept) >= n else items
    rnd = random.Random(seed)
    return rnd.sample(pool, min(n, len(pool)))


def post_text(x: dict) -> str:
    w = (x.get("sift") or {}).get("what")
    w = "" if w in (None, "", "unread") else w
    cap = " ".join((x.get("caption") or "").split())[:220]
    return (f"@{x.get('author', '?')}\nWhat it is: {w or '(you see the post; this is all we can tell you)'}"
            f"\nCaption: {cap}")


def viewer_cut(brief: Path | str, kind: str, caller=None) -> dict:
    text = Path(brief).read_text() if len(str(brief)) < 1000 and Path(str(brief)).exists() else str(brief)
    tpl = newest("viewer-cut").read_text()
    return ask(tpl.replace("{kind}", kind).replace("{brief}", text[:60000]), caller=caller, model=CUT_MODEL)


def ours_text(cut: dict, handle: str) -> str:
    body = "\n".join(cut.get("lines") or [])
    return f"@{handle} · Sponsored\n{body}\nCaption: {cut.get('caption') or '(none)'}"


# ── scoring (code, never the viewer) ───────────────────────────────────────

def _sec(v, length):
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("end", "the end"):
        return float(length or 999)
    if s in ("no", "", "none", "-"):
        return None
    m = re.match(r"(?:(\d+):)?(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    return (int(m.group(1)) * 60 if m.group(1) else 0) + float(m.group(2))


_W = re.compile(r"[a-z0-9$%]+")


def offer_words(cut: dict) -> set:
    """Every word shown or said from the offer onward (the owner, 2026-10-02: "we
    still have to tell people what to do. They're still ads") — a 'pitch' that
    is the offer itself never fails the ad; only pitches before it do."""
    at = cut.get("offer_at")
    words = set()
    for ln in cut.get("lines") or []:
        m = re.match(r"\s*(?:\[(\d+)\]|(\d+):(\d+))", ln)
        start = int(m.group(1)) if m and m.group(1) else (int(m.group(2)) * 60 + int(m.group(3)) if m else None)
        if at is not None and start is not None and start >= float(at) - (0 if m and m.group(1) else 1):
            words |= set(_W.findall(ln.lower()))
    return words


def is_offer(line: str, offer: set) -> bool:
    w = set(_W.findall(str(line or "").lower()))
    return bool(w) and bool(offer) and len(w & offer) / len(w) >= 0.5


def score(answers: list[list[dict]], ours_at: list[int], length_s: float, offer_at, muted: list[int] | None = None,
          offer_set: set | None = None) -> dict:
    """answers[i] = viewer i's posts; ours_at[i] = our post number in their feed.
    Returns the five checks, each {value, passed}, plus `passed` overall."""
    still = not length_s
    mine, real, mine_muted = [], [], []
    for i, (posts, at) in enumerate(zip(answers, ours_at)):
        for p in posts:
            if int(p.get("n", 0)) == at:
                mine.append(p)
                if muted and i in muted:
                    mine_muted.append(p)
            else:
                real.append(p)
    yes = lambda v: str(v).strip().lower().startswith("y")
    n = len(mine)
    stops = sum(yes(p.get("stop")) for p in mine)
    real_rate = (sum(yes(p.get("stop")) for p in real) / len(real)) if real else 0.0
    left = [_sec(p.get("left_at"), length_s) for p in mine]
    ad = [_sec(p.get("ad_at"), length_s) for p in mine]
    offer = float(offer_at) if (offer_at is not None and not still) else None
    stayed = sum(1 for p, l in zip(mine, left) if yes(p.get("stop")) and (offer is None or (l is not None and l >= offer)))
    early_ad = sum(1 for p, a in zip(mine, ad) if a is not None and a < 2 and not yes(p.get("stop")))
    acts = sum(1 for p in mine if yes(p.get("tap")) or (str(p.get("text_friend") or "").strip().lower() not in ("", "nothing")))
    need = n // 2 + 1
    checks = {
        "stop": {"value": f"{stops} of {n}", "passed": stops >= need},
        "beats_feed": {"value": f"{stops / n:.0%} vs {real_rate:.0%}" if n else "-", "passed": n > 0 and stops / n > real_rate},
        "stays_to_offer": {"value": "a still — not scored" if still else
                           (f"{stayed} of {n}" + (f" (offer at {int(offer)}s)" if offer is not None else "")),
                           "passed": True if still else stayed >= need},
        "not_ad_before_stop": {"value": f"{early_ad} clocked it first", "passed": early_ad == 0},
        "would_act": {"value": f"{acts} of {n}", "passed": acts >= need},
    }
    # v2 (Lunev's skeptic + the owner's "we need belief"): asked only of viewers who stopped
    asked = any("believe" in p for p in mine)
    stopped = [p for p in mine if yes(p.get("stop"))]
    if asked:
        bel = sum(1 for p in stopped if str(p.get("believe", "")).strip().lower().startswith("y"))
        fakes = sum(1 for p in stopped if yes(p.get("fake")))
        pitches = sum(1 for p in stopped if yes(p.get("pitch")) and not is_offer(p.get("pitch_line"), offer_set or set()))
        checks["believe"] = {"value": f"{bel} of {len(stopped)} who stopped", "passed": len(stopped) > 0 and bel >= len(stopped) // 2 + 1}
        checks["not_fake"] = {"value": f"{fakes} said it looked fake or staged", "passed": fakes <= 1}
        checks["not_a_pitch"] = {"value": f"{pitches} said it felt like a sales pitch before the offer", "passed": pitches <= 1}
        if mine_muted:
            got = sum(1 for p in mine_muted if yes(p.get("got_it")) and yes(p.get("stop")))
            checks["works_muted"] = {"value": f"{got} of {len(mine_muted)} with the sound off got it",
                                     "passed": got >= len(mine_muted) // 2 + 1}
    return {"checks": checks, "passed": all(c["passed"] for c in checks.values()),
            "mine": mine, "left": left, "ad": ad, "real_stop_rate": real_rate,
            "predicted": predicted(mine, left, length_s, offer, real_rate, stayed, acts), "muted": mine_muted}


def predicted(mine, left, length_s, offer, real_rate, stayed, acts) -> dict:
    """The numbers Meta would show, guessed from the viewers' own seconds.
    A guess until the loop check measures it against live results — never
    shown without saying so. Watch time = the second each viewer swiped (or
    the end); a viewer who never stopped is counted at the second they left."""
    n = len(mine) or 1
    yes = lambda v: str(v).strip().lower().startswith("y")
    stopped = [p for p in mine if yes(p.get("stop"))]
    ns = len(stopped) or 1
    extra = {}
    if any("believe" in p for p in mine):
        did = lambda w: sum(1 for p in stopped if w in str(p.get("do", "")).lower())
        extra = {"believe_rate": round(sum(1 for p in stopped if str(p.get("believe", "")).lower().startswith("y")) / ns, 2),
                 "save_rate": round(did("save") / n, 2), "share_rate": round(did("share") / n, 2),
                 "comment_rate": round(did("comment") / n, 2)}
    if not length_s:                        # a still: no watch time to guess
        return {"kind": "still", "stop_rate": round(sum(yes(p.get("stop")) for p in mine) / n, 2),
                "feed_stop_rate": round(real_rate, 2), "act_rate": round(acts / n, 2), "viewers": len(mine), **extra}
    watch = [min(float(l), length_s) if l is not None else 0.0 for l in left]
    curve = [round(sum(1 for w in watch if w >= t) / n, 2) for t in range(0, int(length_s) + 1)]
    return {"kind": "video", "length_s": length_s,
            "hook_rate": round(sum(yes(p.get("stop")) for p in mine) / n, 2),   # still there at 0:03, the 3-second view
            "feed_stop_rate": round(real_rate, 2),
            "avg_watch_s": round(sum(watch) / n, 1),
            "avg_watch_pct": round(sum(watch) / n / length_s, 2),
            "reach_offer": round(stayed / n, 2) if offer is not None else None,
            "offer_at": offer,
            "act_rate": round(acts / n, 2),
            "retention": curve,                 # share still watching at each second
            "viewers": len(mine), **extra}


def route(sc: dict, length_s: float) -> dict:
    """Where a fail goes, as a role each chain maps to its own step."""
    if sc["passed"]:
        return {"fix_at": None, "at": None}
    mine, left, ad = sc["mine"], sc["left"], sc["ad"]
    c = sc["checks"]
    off = sum(1 for p in mine if any(w in (p.get("felt") or "").lower() for w in OFF_WORDS)
              or str(p.get("for_me", "")).strip().lower() == "no")
    if off >= len(mine) // 2 + 1:
        return {"fix_at": "audience", "at": None}
    early = [l for l in left if l is not None and l <= 2]
    if not c["stop"]["passed"] or not c["beats_feed"]["passed"] or len(early) >= len(mine) // 2 + 1:
        return {"fix_at": "openings", "at": "0:00–0:02"}
    if not c["stays_to_offer"]["passed"]:
        # Most of them clocked it as an ad at the same moment: that moment is
        # what loses them, whatever second each finally swiped at.
        clocked = [a for a in ad if a is not None]
        if len(clocked) >= len(mine) // 2 + 1:
            m = statistics.median(clocked)
            if sum(1 for a in clocked if abs(a - m) <= 2) >= len(mine) // 2 + 1:
                return {"fix_at": "giveaway", "at": f"0:{int(m):02d}"}
        ls = [l for l in left if l is not None]
        return {"fix_at": "middle", "at": f"0:{int(statistics.median(ls)):02d}" if ls else None}
    if not c["not_ad_before_stop"]["passed"]:
        return {"fix_at": "openings", "at": "0:00–0:02"}
    if "not_fake" in c and not c["not_fake"]["passed"]:
        return {"fix_at": "staged", "at": None}          # how a shot is directed reads fake
    if "not_a_pitch" in c and not c["not_a_pitch"]["passed"]:
        return {"fix_at": "words", "at": None}           # the lines sound like selling
    if "works_muted" in c and not c["works_muted"]["passed"]:
        return {"fix_at": "muted", "at": None}           # the on-screen words don't carry it alone
    if "believe" in c and not c["believe"]["passed"]:
        return {"fix_at": "proof", "at": None}           # they stopped but don't buy it
    if "belief" in c and not c["belief"]["passed"]:
        return {"fix_at": "proof", "at": None}           # it doesn't give the reasons real buyers bought
    return {"fix_at": "close", "at": None}


def writer_notes(sc: dict, rt: dict) -> str:
    """What the writing step is handed on a re-make — the viewers' own words."""
    lines = [f"## WHAT THE VIEWERS DID — fix {say(rt['fix_at'])}" + (f" (around {rt['at']})" if rt.get("at") else ""),
             "",
             f"{len(sc['mine'])} people from this avatar scrolled the finished ad inside their real feed. "
             "Their reactions, word for word. Fix what made them leave or pass — inside the "
             "swipe's locked structure (adapt, never rebuild; a structural change still needs "
             "the owner's numbered approval). Do not add claims, people or facts no source gives.",
             ""]
    for i, p in enumerate(sc["mine"], 1):
        lines.append(f"- Viewer {i}: stopped {p.get('stop')}, left at {p.get('left_at')}, "
                     f"clocked as an ad at {p.get('ad_at')}. Felt: \"{p.get('felt', '')}\" "
                     + (f"Giveaway: \"{p.get('ad_tell')}\" " if p.get("ad_tell") else "")
                     + f"Tap: {p.get('tap')} — \"{p.get('tap_why', '')}\""
                     + (f" Believe: {p.get('believe')}" + (f" — doubt: \"{p.get('doubt')}\"" if p.get("doubt") else "") if "believe" in p else "")
                     + (f" Looked fake: \"{p.get('fake_what')}\"" if str(p.get("fake", "")).lower().startswith("y") else "")
                     + (f" Felt like a pitch: \"{p.get('pitch_line')}\"" if str(p.get("pitch", "")).lower().startswith("y") and not p.get("_offer_pitch") else ""))
    return "\n".join(lines)


# ── worth making? (asked right before anything costs real credits) ────────

def brief_key(text: str) -> str:
    """What the stamp is tied to: the brief's json block — its truth, which a
    later stamp line (swipe match, manifest, the owner's read) never changes — or
    the whole text when it has none."""
    import hashlib
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text, re.S)
    return hashlib.md5((blocks[-1] if blocks else text).encode()).hexdigest()[:12]


def stamp_of(run_dir, brief_text: str) -> dict | None:
    """The viewer stamp for THIS brief, or None if it was never checked or
    has changed since."""
    f = Path(run_dir) / "viewer-check" / "STAMP.json"
    if not f.exists():
        return None
    st = json.loads(f.read_text())
    return st if st.get("brief") == brief_key(brief_text) else None


def worth_making(run_dir, brand, avatar, brief, kind="video", sub=None, handle=None, caller=None) -> tuple[bool, str, dict]:
    """Production's question before it spends: has this exact brief passed
    the viewers? A stamp answers at no cost; a brief never checked is checked
    now (text only, cents) — the work is done before the money, never after.
    Returns (ok, why, stamp)."""
    text = Path(brief).read_text() if len(str(brief)) < 1000 and Path(str(brief)).exists() else str(brief)
    st = stamp_of(run_dir, text)
    if st and st.get("approved"):
        return True, "passed by the owner (V)", st
    if not st:
        if not avatar:
            return False, "no avatar on the run, so no viewer can be built", {}
        r = check(run_dir, brand, avatar, text, kind=kind, sub=sub, round_n=_next_round(run_dir),
                  handle=handle, caller=caller)
        st = stamp_of(run_dir, text) or {}
    p = st.get("predicted") or {}
    nums = (f"hook {p.get('hook_rate', p.get('stop_rate', 0)):.0%} vs feed {p.get('feed_stop_rate', 0):.0%}"
            + (f" · avg watch {p['avg_watch_s']}s of {int(p['length_s'])}s · reach offer {p['reach_offer']:.0%}"
               if p.get("kind") == "video" and p.get("reach_offer") is not None else "")
            + f" · would act {p.get('act_rate', 0):.0%}")
    if st.get("passed"):
        return True, "viewers passed it — " + nums, st
    return False, (f"the viewers did not pass it (goes back to the {st.get('fix_at')}) — " + nums
                   + f" · see {st.get('folder')}/VERDICT.md"), st


def _next_round(run_dir) -> int:
    d = Path(run_dir) / "viewer-check"
    got = [int(x.name[1:]) for x in d.glob("r*") if x.name[1:].isdigit()] if d.is_dir() else []
    return max(got, default=0) + 1


def approve(run_dir, brief) -> dict:
    """the owner's V, written into the stamp for this exact brief."""
    text = Path(brief).read_text() if len(str(brief)) < 1000 and Path(str(brief)).exists() else str(brief)
    f = Path(run_dir) / "viewer-check" / "STAMP.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    st = json.loads(f.read_text()) if f.exists() else {}
    st.update(brief=brief_key(text), approved=True, passed=True)
    f.write_text(json.dumps(st, indent=1) + "\n")
    return st


SAY = {"openings": "the openings", "middle": "the middle", "giveaway": "the moment it read as an ad",
       "close": "the close", "audience": "who it's for (the owner's call)", "staged": "the shot that looks fake or staged",
       "words": "the lines that sound like a sales pitch", "muted": "the on-screen words (sound off)",
       "proof": "the proof: why they'd believe it",
       "diversity": "what makes it a new ad to Meta (who, awareness, format, face, place, look)"}


def diversity(brand: str, brief_text: str, run_dir=None) -> dict | None:
    """Is this brief a new creative to Meta? Its seven moves, read off the words,
    against what's running and against briefs already written for the brand.
    None when the creative-diversity machine isn't there; never blocks on its own
    error. Off: QC_DIVERSITY=0."""
    if os.environ.get("QC_DIVERSITY", "1") == "0" or "unittest" in sys.modules:
        return None
    cd = WS / "components" / "creative-diversity"
    if not (cd / "brief_view.py").exists():
        return None
    try:
        sys.path.insert(0, str(cd))
        import brief_view as BV, check as DK, matrix as DM
        t = BV.read_moves(brand, brief_text)
        mv = DM.moves({"sub_avatar": t.get("sub_avatar"), "awareness": t.get("awareness"), "angle": t.get("angle"),
                       "format": t.get("format"), "setting": t.get("setting"), "style": t.get("style"),
                       "face": BV._face(t.get("face"))})
        run = DK.score(brand, mv)
        need = DK.DIMS["rule"]["min_moves"]
        # briefs already written for this brand (their recorded moves), this one's own row excluded by run
        reg = WS / "brands" / brand / "briefs" / "briefs.json"
        near = None
        if reg.exists():
            for b in json.loads(reg.read_text()).get("briefs", []):
                if b.get("moves") and (not run_dir or Path(run_dir).name not in json.dumps(b)):
                    d, diff = DM.distance(mv, b["moves"])
                    if near is None or d < near[0]:
                        near = (d, b.get("brief"), [k for k in DM.BIG if k not in diff])
        bad_run = run.get("verdict") == "variation"
        bad_brief = near is not None and near[0] <= DK.DIMS["rule"]["variation_at_or_below"]
        note = []
        if bad_run:
            note.append(f"It is {run['moves_apart']} move(s) from an ad already running (same {', '.join(run.get('same_on') or [])}).")
        if bad_brief:
            note.append(f"It is {near[0]} move(s) from {near[1]}, a brief already written (same {', '.join(near[2])}).")
        return {"moves": mv, "why": t.get("why"), "running": {k: run.get(k) for k in ("verdict", "moves_apart", "nearest", "same_on")},
                "nearest_brief": {"moves": near[0], "brief": near[1], "same_on": near[2]} if near else None,
                "passed": not (bad_run or bad_brief), "need": need, "note": " ".join(note),
                "value": f"{run.get('moves_apart')} moves from the nearest running ad"
                         + (f" · {near[0]} from {near[1]}" if near else "")}
    except Exception as e:  # noqa: BLE001 — the diversity read never blocks a run by failing itself
        return {"error": f"{type(e).__name__}: {str(e)[:160]}"}


def say(role) -> str:
    return SAY.get(role, str(role))


# ── the real objections (the viewers stay blind to the bank) ─────────────

BANK_FILES = ("core-avatars/objection-bank.md", "customer-experience/objection-bank.md", "offers/objection-answers.md")


def bank_missing(brand: str, names=BANK_FILES) -> list[str]:
    """The objection files this brand's folder lacks, as workspace paths —
    named out loud, never created, never a refusal (SI-140)."""
    return [str(Path("brands", brand, n)) for n in names if not _brand(brand, *n.split("/")).exists()]


def bank_text(brand: str, avatar: str | None = None) -> str:
    """Every objection file the brand keeps, objections and answers both, plus
    the answers the viewer chain found in real customer data for this avatar.
    A file the brand lacks is named in a header line, so the match knows it
    ran on part of the bank."""
    files = [_brand(brand, *n.split("/")) for n in BANK_FILES]
    if avatar:
        files.append(ANSWERS / f"{brand}--{avatar}.md")
    out = [f"=== missing: {m} (not in this brand's folder) ===" for m in bank_missing(brand)]
    for f in files:
        if f.exists():
            out.append(f"=== {f.relative_to(WS) if WS in f.parents else f} ===\n{f.read_text(errors='replace')}")
    return "\n\n".join(out)[:90000]


def objections(mine: list[dict], brand: str, avatar: str, caller=None) -> dict:
    """Match what the viewers doubted, called a pitch, or would comment to the
    brand's own objection bank, quoting the bank's answer. Run AFTER the
    viewers, never shown to them, so their doubts are their own."""
    said = []
    for i, p in enumerate(mine, 1):
        for k, kind in (("doubt", "doubt"), ("pitch_line", "pitch"), ("comment", "comment"), ("fake_what", "doubt")):
            if k == "pitch_line" and p.get("_offer_pitch"):
                continue                      # the offer is allowed to sell
            v = str(p.get(k) or "").strip()
            if v and v.lower() not in ("nothing", "none", "n/a"):
                said.append(f"- viewer {i} ({kind}): {v}")
    bank = bank_text(brand, avatar)
    missing = bank_missing(brand)
    if not said or (len(missing) == len(BANK_FILES) and not (ANSWERS / f"{brand}--{avatar}.md").exists()):
        return {"matches": [], "likely_comments": [], "new_objections": [], "bank_missing": missing,
                "skipped": "nothing to match" if not said else "no objection bank on file"}
    tpl = newest("objection-match").read_text()
    got = ask(tpl.replace("{brand}", brand).replace("{avatar}", avatar).replace("{said}", "\n".join(said))
              .replace("{bank}", bank), caller=caller, model=CUT_MODEL)
    if isinstance(got, dict):
        got["bank_missing"] = missing
    return got


# ── answers from real data (the owner, 2026-10-02: "everything needs to come from real data") ──

ANSWERS = RECORDS / "objection-answers"
REAL_PEOPLE = {"customer", "churned", "lead", "commenter", "prospect"}   # never the brand's or a creator's own lines
PROOF_USES = {"post-use-feeling", "transformation-reaction", "objection", "refund-reason", "expectation-gap",
              "what-they-like", "why-bought", "buying-criteria", "shopping-experience", "service-feedback",
              "peer-advice", "comment", "competitor-annoyance", "alternative-solution", "unanswered-question"}


def _rows(brand: str, avatar: str) -> list[dict]:
    """The brand's real language rows: every row for this avatar, plus other
    avatars' customers and refunders on results, doubts and refunds."""
    q = str(WS / "components" / "language-layer")
    if not Path(q).is_dir():
        q = str(WS / "tools" / "language-layer")
    if q not in sys.path:
        sys.path.insert(0, q)
    from language_layer import engine as LE
    rows = LE.load(brand)
    use = lambda r: set([r.get("use")] if isinstance(r.get("use"), str) else (r.get("use") or []))
    core = None
    try:
        core = next((d.name for d in _brand(brand, "core-avatars").iterdir()
                     if (d / "sub-avatars").is_dir() and any(avatar in x.name for x in (d / "sub-avatars").iterdir())), None)
    except Exception:
        pass
    rows = [r for r in rows if r.get("speaker") in REAL_PEOPLE]
    mine = [r for r in rows if r.get("avatar") in (avatar, core) or r.get("sub") == avatar]
    other = [r for r in rows if r not in mine and r.get("speaker") in ("customer", "churned") and use(r) & PROOF_USES]
    return mine + other


def find_answers(brand: str, avatar: str, worries: list[str], label: str = "", caller=None) -> dict:
    """For each worry no bank answers: the real lines that answer it, quoted
    word for word with their row id. A quote that isn't in its row is dropped."""
    import sys as _s  # noqa: F401
    worries = [w for w in dict.fromkeys(x.strip() for x in worries if x and x.strip())]
    if not worries:
        return {"answers": []}
    rows = _rows(brand, avatar)
    by_id = {r["id"]: r for r in rows if r.get("id")}
    if len(rows) > 2500:   # rank by shared words with the worries; the words still come from the rows
        want = set(w for w in words_only(" ".join(worries)).split() if len(w) > 3)
        rows = sorted(rows, key=lambda r: -len(want & set(words_only(r.get("text", "")).split())))[:2500]
    text = "\n".join(f"[{r['id']}] ({r.get('avatar')} · {r.get('speaker')} · {r.get('use') if isinstance(r.get('use'), str) else ','.join(r.get('use') or [])}) "
                     f"{' '.join(str(r.get('text', '')).split())}" for r in rows)[:900000]
    tpl = newest("answer-find").read_text()
    got = ask(tpl.replace("{brand}", brand).replace("{avatar}", avatar).replace("{worries}", "\n".join(f"- {w}" for w in worries))
              .replace("{rows}", text), caller=caller, model=CUT_MODEL)
    dropped = 0
    for a in got.get("answers") or []:
        for k in ("answer_lines", "echo_lines"):
            keep = []
            for ln in a.get(k) or []:
                r = by_id.get(ln.get("id") if isinstance(ln, dict) else ln)
                if r:   # the words always come from the row itself, never retyped
                    src = r.get("source") or {}
                    keep.append({"id": r["id"], "quote": " ".join(str(r.get("text", "")).split()), "avatar": r.get("avatar"),
                                 "who": r.get("speaker"), "source": src.get("name") or src.get("id")})
                else:
                    dropped += 1
            a[k] = keep
        a["found"] = bool(a.get("answer_lines"))
    got["dropped_unverified"] = dropped
    import datetime
    ANSWERS.mkdir(parents=True, exist_ok=True)
    f = ANSWERS / f"{brand}--{avatar}.md"
    head = "" if f.exists() else (f"# Answers from real data · {avatar} ({brand})\n\nWorries viewers raised that the objection bank "
                                  "didn't answer, answered only with real lines from the brand's language bank (survey responses, "
                                  "refunds, comments), each with its row id and checked word for word. Any real customer's line may go on "
                                  "screen as a quoted review, word for word (the owner, 2026-10-03).\n")
    out = [f"\n## {datetime.date.today().isoformat()} · {label}"]
    for a in got.get("answers") or []:
        out.append(f"\n### {a.get('worry')}")
        if a.get("answer_lines"):
            out.append(f"(Summary, not a quote: {a.get('how_it_answers', '')})")
            out += [f"- \"{ln['quote']}\" — {ln.get('who')}, {ln.get('avatar')} · {ln.get('source')} · `{ln['id']}`" for ln in a["answer_lines"]]
        else:
            out.append("No real answer found yet: we don't have the proof for this.")
        if a.get("echo_lines"):
            out.append("People really say this:")
            out += [f"- \"{ln['quote']}\" · `{ln['id']}`" for ln in a["echo_lines"][:3]]
    with f.open("a") as fh:
        fh.write(head + "\n".join(out) + "\n")
    got["file"] = str(f)
    return got


# ── the belief index (the owner, 2026-10-03: "believability has to do with what the
#    data actually shows made customers believe in the brand and buy … that's
#    the core index to roll on") ─────────────────────────────────────────────

BELIEF = RECORDS / "belief-index"
BELIEF_TOP = 6            # the top reasons by share are the ones that count
BELIEF_NEED = 2           # an ad must actually give at least this many of them


def belief_index(brand: str) -> dict:
    f = BELIEF / f"{brand}.json"
    return json.loads(f.read_text()) if f.exists() else {}


def belief_drivers(cut: dict, brand: str, caller=None) -> dict:
    """Which of the reasons real customers gave for buying the ad actually
    gives the viewer. Judged on what a viewer sees, never on claims."""
    idx = belief_index(brand)
    themes = [t for t in idx.get("themes") or [] if not re.search(r"curious|gift", t["theme"], re.I)][:BELIEF_TOP]
    if not themes:
        return {"skipped": "no belief index for this brand"}
    text = "\n".join(f"- {t['theme']} — {t['count']} of {idx.get('total')} customers ({t['share']:.0%}). e.g. "
                     + " | ".join(f"\"{e['quote'][:140]}\"" for e in t["examples"][:3]) for t in themes)
    tpl = newest("belief-drivers").read_text()
    got = ask(tpl.replace("{brand}", brand).replace("{index}", text).replace("{cut}", "\n".join(cut.get("lines") or [])),
              caller=caller, model=CUT_MODEL)
    ds = got.get("drivers") or []
    given = [d for d in ds if str(d.get("in_ad", "")).lower() == "yes"]
    missing = [d for d in ds if str(d.get("in_ad", "")).lower() == "no"]
    proof = [d for d in given if re.search(r"result|review|testimon", str(d.get("reason", "")), re.I)]
    # the owner, 2026-10-03: at least one of the two proof reasons (real results or reviews) must be there.
    return {"drivers": ds, "given": len(given), "missing": [d.get("reason") for d in missing], "proof": len(proof),
            "passed": len(given) >= BELIEF_NEED and len(proof) >= 1, "need": BELIEF_NEED, "themes": themes,
            "total": idx.get("total")}


# ── hidden by the app (a rule; the boxes come from the frame) ─────────────

ZONES = {   # % of a 1080×1920 frame: top, bottom, left, right
    "Reels": {"top": 14, "bottom": 35, "left": 6, "right": 6, "exact": True},
    "TikTok": {"top": 8, "bottom": 26, "left": 4, "right": 14, "exact": False},
    "Shorts": {"top": 10, "bottom": 25, "left": 4, "right": 10, "exact": False},
}


def _ask_image(text: str, image: Path, caller=None) -> dict:
    if caller:
        return caller(text, 0.0, True)
    if os.environ.get("VIEWER_HAND_DIR") or ENGINE == "claude":
        return _hand(text, True, image=str(image))
    import base64, mimetypes
    mime = mimetypes.guess_type(str(image))[0] or "image/png"
    body = {"contents": [{"parts": [{"inline_data": {"mime_type": mime, "data": base64.b64encode(Path(image).read_bytes()).decode()}},
                                    {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    req = urllib.request.Request(f"{BASE}/{CUT_MODEL}:generateContent?key={_key()}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    return _json("".join(p.get("text", "") for p in parts) or "{}")


def hidden_by_app(images, caller=None) -> list[dict]:
    """For each frame: where the faces, product and words sit, and which of
    them fall under each app's buttons and caption. Boxes are 0–1000."""
    tpl = newest("hidden-boxes").read_text()
    out = []
    for img in images:
        img = Path(img)
        try:
            items = (_ask_image(tpl, img, caller=caller) or {}).get("items") or []
        except Exception as e:
            out.append({"frame": img.name, "error": f"{type(e).__name__}: {str(e)[:120]}"}); continue
        hits = []
        for it in items:
            b = it.get("box") or []
            if len(b) != 4:
                continue
            x0, y0, x1, y1 = [v / 10 for v in b]          # → %
            area = max((x1 - x0) * (y1 - y0), 1e-6)
            for app, z in ZONES.items():
                safe = (z["left"], z["top"], 100 - z["right"], 100 - z["bottom"])
                ix = max(0, min(x1, safe[2]) - max(x0, safe[0])); iy = max(0, min(y1, safe[3]) - max(y0, safe[1]))
                covered = 1 - (ix * iy) / area
                if covered > 0.25:
                    hits.append({"app": app, "what": it.get("what"), "label": it.get("label"),
                                 "covered": round(covered, 2), "exact": z["exact"]})
        out.append({"frame": img.name, "items": items, "hidden": hits})
    return out


# ── fix and learn: a fail is rewritten, a pass teaches the chain ──────────

LEARN = RECORDS / "learnings"


def learnings_file(brand: str, avatar: str) -> Path:
    return LEARN / f"{brand}--{avatar}.md"


def learnings(brand: str, avatar: str, limit: int = 12000) -> str:
    """What got past this avatar before, newest last (read by the fixer and by
    every writing stage of the video and statics chains)."""
    f = learnings_file(brand, avatar)
    return f.read_text()[-limit:] if f.exists() else ""


def language_text(brand: str, avatar: str) -> str:
    """This avatar's REAL lines (survey answers, comments), verbatim with ids —
    the only words the rewrite may quote — plus the avatar's language rules."""
    out = []
    rules = _brand(brand, "core-avatars", avatar, "language", "rules.md")
    if rules.exists():
        out.append(f"=== how to talk to them (rules, not quotes) ===\n{rules.read_text(errors='replace')[:8000]}")
    try:
        rows = [r for r in _rows(brand, avatar) if r.get("avatar") == avatar or r.get("sub") == avatar]
    except Exception:
        rows = []
    out.append("=== real lines (quote only these, word for word) ===\n" +
               "\n".join(f"[{r.get('id')}] {' '.join(str(r.get('text', '')).split())}" for r in rows))
    return "\n\n".join(out)[:60000]


def fix(brief_text: str, r: dict, brand: str, avatar: str, caller=None, refused: str = "") -> tuple[str, dict]:
    """Rewrite only what the viewers passed on, answering their doubts with the
    brand's own objection answers and the customers' own words."""
    tpl = newest("viewer-fix").read_text()
    sent = (tpl.replace("{brand}", brand).replace("{avatar}", avatar).replace("{fix_at}", say(r.get("fix_at")))
               .replace("{notes}", (r.get("notes") or "(none)") + (f"\n\nYOUR LAST ATTEMPT WAS REFUSED: {refused}. Fix that and keep to the rules." if refused else "")).replace("{learnings}", learnings(brand, avatar) or "(nothing yet)")
               .replace("{language}", language_text(brand, avatar) or "(no language bank on file)").replace("{brief}", brief_text))
    out = ask(sent, as_json=False, caller=caller, model=CUT_MODEL)
    m = re.search(r"=== BRIEF ===\s*(.*?)\s*=== END BRIEF ===", out, re.S)
    c = re.search(r"=== CHANGES ===\s*(.*?)\s*=== END CHANGES ===", out, re.S)
    if not m:
        raise ValueError("the fixer returned no brief")
    # The offer is the website's wording: a rewrite that changes a price or
    # guarantee line is refused, whatever else it fixed (caught 2026-10-02: a
    # product's ™ quietly dropped off the price card).
    kept = [ln.strip() for ln in brief_text.splitlines() if re.search(r"\$\s?\d", ln)]
    for ln in kept:
        core = re.findall(r'"([^"]*\$\s?\d[^"]*)"', ln) or [ln]
        for line in core:
            if line.strip() and line.strip() not in m.group(1):
                raise ValueError(f"the rewrite changed an offer line, which must stay word for word: {line.strip()[:90]}")
    try:
        changes = _json(c.group(1)) if c else {}
    except ValueError:
        changes = {"changes": [], "unreadable": c.group(1)[:500] if c else ""}
    # Everything from real data (the owner, 2026-10-02). Any line the rewrite puts
    # in quotes must exist word for word in the brand's real language or in the
    # answers found from it — not in the viewers' words, not in the bank's advice.
    real = _real_text(brand, avatar)
    if isinstance(changes, dict):
        changes["bank_missing"] = bank_missing(brand, BANK_FILES[:2])   # the two files _real_text reads
    if real:
        norm = words_only
        for ch in changes.get("changes") or []:
            for q in re.findall(r'[“"]([^“”"]{12,})[”"]', str(ch.get("now", ""))):
                if norm(q) in norm(brief_text):
                    continue                    # the offer line or words already in the brief
                if norm(q) not in real:
                    raise ValueError(f"the rewrite quoted words that aren't in the real data: {q[:80]}")
    return m.group(1).strip() + "\n", changes


def words_only(x) -> str:
    """Word-for-word comparison that ignores punctuation, quote marks and case."""
    return " ".join(re.findall(r"[a-z0-9$%]+", str(x).lower()))


def _real_text(brand: str, avatar: str) -> str:
    """Every real line the rewrite may quote, normalised for a word-for-word check:
    the language rows, the answers found in them, the language bank, and the
    customer phrases the objection bank quotes (in quote marks), never its advice.
    Which of its two objection files the brand lacks, fix() records."""
    try:
        rows = _rows(brand, avatar)
    except Exception:
        rows = []
    parts = [str(r.get("text", "")) for r in rows]
    af = ANSWERS / f"{brand}--{avatar}.md"
    if af.exists():   # only the verified quote lines, never the summaries
        parts += re.findall(r'^- "(.*)" — ', af.read_text(errors="replace"), re.M)
    for f in (_brand(brand, *n.split("/")) for n in BANK_FILES[:2]):
        if f.exists():
            parts += re.findall(r'[“"]([^“”"]{6,})[”"]', f.read_text(errors="replace"))
    return " | ".join(words_only(x) for x in parts)


def learn(brand: str, avatar: str, label: str, failed: list[dict], passed: dict, changes: list[dict]) -> Path:
    """A pass after a fail is written down: what failed, what changed, what it
    rested on, and the numbers after. Every later brief for this avatar reads it."""
    import datetime
    LEARN.mkdir(parents=True, exist_ok=True)
    f = learnings_file(brand, avatar)
    head = "" if f.exists() else (f"# What got past {avatar} ({brand})\n\nWritten by the viewer chain each time a brief "
                                  "failed the viewers and then passed. Read by the fixer and by every writing stage.\n")
    p = passed.get("predicted") or {}
    fails = []
    for r in failed:
        fails += [f"{k.replace('_', ' ')} ({c['value']})" for k, c in (r.get("checks") or {}).items() if not c.get("passed")]
    lines = [f"\n## {datetime.date.today().isoformat()} · {label}",
             f"- Failed on: {', '.join(dict.fromkeys(fails)) or 'n/a'}"]
    for ch in changes:
        lines.append(f"- Changed {ch.get('where', '?')}: \"{ch.get('was', '')}\" → \"{ch.get('now', '')}\" "
                     f"(answers: {ch.get('why', '')}; from {ch.get('source', '')})")
    nums = ", ".join(x for x in [f"believe {p['believe_rate']:.0%}" if "believe_rate" in p else "",
                                 f"stopped {p.get('hook_rate', p.get('stop_rate', 0)):.0%}",
                                 f"would act {p.get('act_rate', 0):.0%}"] if x)
    lines.append(f"- Then passed: {nums}")
    with f.open("a") as fh:
        fh.write(head + "\n".join(lines) + "\n")
    return f


def note_new_objections(brand: str, avatar: str, label: str, items: list[str]) -> Path | None:
    """Worries the viewers raised that the objection bank has no answer for —
    kept per avatar so they get answered from real customer data, never invented."""
    items = [i for i in dict.fromkeys(x.strip() for x in items if x and x.strip())]
    if not items:
        return None
    import datetime
    d = RECORDS / "new-objections"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{brand}--{avatar}.md"
    head = "" if f.exists() else (f"# New objections · {avatar} ({brand})\n\nRaised by viewer-chain viewers, not answered by the "
                                  "objection bank. Each needs an answer from real customer data before a rewrite can use it.\n")
    with f.open("a") as fh:
        fh.write(head + f"\n## {datetime.date.today().isoformat()} · {label}\n" + "\n".join(f"- {i}" for i in items) + "\n")
    return f


# ── the page a person opens ────────────────────────────────────────────────

def _changes_html(r: dict) -> str:
    import html as H
    e = lambda x: H.escape(str(x if x is not None else ""))
    hist = r.get("history") or []
    ch = r.get("changes") or []
    if not hist and not ch:
        return ""
    rounds = "".join(f'<span style="padding:6px 10px;border-radius:999px;font-size:.82rem;background:{"var(--pass-soft)" if h.get("passed") else "var(--fail-soft)"};color:{"var(--pass)" if h.get("passed") else "var(--fail)"}">round {e(h.get("round"))}: {"passed" if h.get("passed") else "failed · " + e(say(h.get("fix_at")))}</span>' for h in hist)
    rows = "".join(f"<tr><td>{e(c.get('where'))}</td><td>{e(c.get('was'))}</td><td><b>{e(c.get('now'))}</b></td><td>{e(c.get('why'))}<small>{e(c.get('source'))}</small></td></tr>" for c in ch)
    return (f'<section><h2>How it got there</h2><div style="display:flex;flex-wrap:wrap;gap:8px">{rounds}</div>'
            + (f'<div class="t"><table><thead><tr><th>Where</th><th>Was</th><th>Now</th><th>Answers · source</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else "")
            + ("<p style='font-size:.85rem;color:var(--muted)'>What made it pass is saved for this avatar, so the next brief starts with it.</p>" if r.get("passed") and ch else "")
            + "</section>")


def _belief_html(r: dict) -> str:
    import html as H
    e = lambda x: H.escape(str(x if x is not None else ""))
    bd = r.get("belief") or {}
    if not bd.get("drivers"):
        return ""
    share = {t["theme"]: t["share"] for t in bd.get("themes") or []}
    rows = "".join(f'<tr><td>{e(d.get("reason"))}<small>{share.get(d.get("reason"), 0):.0%} of buyers said this</small></td>'
                   f'<td>{"✅" if str(d.get("in_ad")).lower() == "yes" else ("—" if str(d.get("in_ad")).lower() == "n/a" else "❌")}</td><td>{e(d.get("where"))}</td></tr>'
                   for d in bd["drivers"])
    return (f'<section><h2>Why real customers bought, and does this ad give it?</h2>'
            f'<p style="color:var(--muted);font-size:.85rem">From {e(bd.get("total") or "the")} customers’ answers to "what gut instinct made you buy?". Belief passes when the ad gives at least {bd.get("need")} of these.</p>'
            f'<div class="t"><table><thead><tr><th>Reason buyers gave</th><th>In this ad</th><th>Where</th></tr></thead><tbody>{rows}</tbody></table></div></section>')


def report_html(r: dict, brand: str, avatar: str, title: str = "") -> str:
    import html as H
    e = lambda x: H.escape(str(x if x is not None else ""))
    ok = r.get("passed")
    p = r.get("predicted") or {}
    checks = r.get("checks") or {}
    mine = r.get("mine") or []
    ob = r.get("objections") or {}
    frames = r.get("frames") or []
    def light(k, c):
        return f'<div class="lt {"on" if c["passed"] else "off"}"><i></i><b>{e(k.replace("_", " "))}</b><span>{e(c["value"])}</span></div>'
    curve = p.get("retention") or []
    W, Hh = 300, 90
    pts = " ".join(f"{10 + i / max(len(curve) - 1, 1) * (W - 20):.1f},{Hh - 10 - v * (Hh - 20):.1f}" for i, v in enumerate(curve))
    nums = []
    if p.get("kind") == "video":
        nums = [(f"{p['hook_rate']:.0%}", f"stopped · real posts {p['feed_stop_rate']:.0%}"), (f"{p['avg_watch_s']}s", f"avg watch of {int(p['length_s'])}s"),
                (f"{p['reach_offer']:.0%}" if p.get("reach_offer") is not None else "–", "reach the price"), (f"{p['act_rate']:.0%}", "would tap or tell a friend")]
    elif p:
        nums = [(f"{p.get('stop_rate', 0):.0%}", f"stopped · real posts {p.get('feed_stop_rate', 0):.0%}"), (f"{p.get('act_rate', 0):.0%}", "would tap or tell a friend")]
    if "believe_rate" in p:
        nums += [(f"{p['believe_rate']:.0%}", "believe it would work"), (f"{p['save_rate']:.0%}", f"save · share {p['share_rate']:.0%} · comment {p['comment_rate']:.0%}")]
    faces = ["#E8B48A", "#8D5A3B", "#C68B59", "#5C3A21", "#F1C9A0"]
    viewers = "".join(
        f'<div class="vw"><svg viewBox="0 0 40 40"><circle cx="20" cy="20" r="18" fill="{faces[i % 5]}"/><circle cx="14" cy="17" r="2.2" fill="#1b1b1b"/><circle cx="26" cy="17" r="2.2" fill="#1b1b1b"/>'
        f'<path d="M13 27q7 {"5" if str(m.get("stop","")).lower().startswith("y") else "-4"} 14 0" stroke="#1b1b1b" stroke-width="2.2" fill="none" stroke-linecap="round"/></svg>'
        f'<div><b>Viewer {i + 1}</b>{" · 🔇" if i in (1, 3) and p.get("kind") == "video" else ""}<span>stop {e(m.get("stop"))} · left {e(m.get("left_at"))} · tap {e(m.get("tap"))}'
        f'{" · believe " + e(m.get("believe")) if "believe" in m else ""}</span><q>{e(m.get("felt"))}</q>'
        f'{"<em>doubt: " + e(m.get("doubt")) + "</em>" if m.get("doubt") else ""}</div></div>' for i, m in enumerate(mine))
    matches = "".join(f'<tr><td>V{e(x.get("viewer"))}</td><td>{e(x.get("said"))}</td><td>{e(x.get("objection"))}<small>{e(x.get("where"))}</small></td><td>{e(x.get("answer"))}</td></tr>'
                      for x in ob.get("matches") or [])
    likely = "".join(f"<li>“{e(c.get('comment'))}” <small>{e(c.get('objection'))}</small></li>" for c in ob.get("likely_comments") or [])
    newob = "".join(f"<li>{e(x)}</li>" for x in ob.get("new_objections") or [])
    fr = ""
    for f in frames:
        hid = f.get("hidden") or []
        fr += f'<div class="fr"><b>{e(f.get("frame"))}</b>' + ("<span class=ok>nothing under the app</span>" if not hid and not f.get("error") else "") + \
              (f'<span class=bad>{e(f.get("error"))}</span>' if f.get("error") else "") + \
              "".join(f'<span class=bad>{e(h["label"])} ({e(h["what"])}) under {e(h["app"])}{"" if h["exact"] else " ≈"} · {int(h["covered"]*100)}%</span>' for h in hid) + "</div>"
    return f"""<title>{e(title or "Viewer chain")}</title>
<style>
:root{{--bg:#F2F3F6;--panel:#fff;--fg:#16181D;--muted:#5D6270;--line:#DADDE4;--accent:#2B54E8;--pass:#1E7A4A;--pass-soft:#DFF2E7;--fail:#B4322A;--fail-soft:#F8E1DF;--warn:#9A6400}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#111318;--panel:#1A1D24;--fg:#E9EBF0;--muted:#9BA1AF;--line:#2C303A;--accent:#7D9BFF;--pass:#5FCB90;--pass-soft:#16301F;--fail:#F08479;--fail-soft:#3A1A17;--warn:#E3B055;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#111318;--panel:#1A1D24;--fg:#E9EBF0;--muted:#9BA1AF;--line:#2C303A;--accent:#7D9BFF;--pass:#5FCB90;--pass-soft:#16301F;--fail:#F08479;--fail-soft:#3A1A17;--warn:#E3B055;color-scheme:dark}}
*{{box-sizing:border-box}}body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,sans-serif;margin:0}}
.w{{max-width:960px;margin:0 auto;padding-inline:18px;padding-block:28px 60px;display:flex;flex-direction:column;gap:26px}}
h1{{font:800 clamp(1.8rem,5vw,2.6rem)/1.1 system-ui;margin:0}}h2{{font:800 1.3rem/1.2 system-ui;margin:0}}
.ban{{border-radius:16px;padding:16px 18px;font:700 1.15rem/1.3 system-ui;background:{"var(--pass-soft)" if ok else "var(--fail-soft)"};color:{"var(--pass)" if ok else "var(--fail)"}}}
.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}}
.n{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px}}.n b{{display:block;font:800 1.5rem/1 system-ui}}.n span{{font-size:.8rem;color:var(--muted)}}
.lts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px}}
.lt{{display:grid;grid-template-columns:14px 1fr;gap:2px 8px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px}}.lt i{{width:12px;height:12px;border-radius:50%;margin-top:4px;grid-row:span 2}}
.lt.on i{{background:var(--pass)}}.lt.off i{{background:var(--fail)}}.lt span{{font-size:.8rem;color:var(--muted)}}
.vws{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}}
.vw{{display:grid;grid-template-columns:40px 1fr;gap:10px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px}}.vw svg{{width:40px;height:40px}}
.vw span{{display:block;font-size:.78rem;color:var(--muted)}}.vw q{{display:block;margin-top:4px}}.vw em{{display:block;font-size:.85rem;color:var(--fail);margin-top:4px;font-style:normal}}
.t{{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:14px}}table{{border-collapse:collapse;width:100%;font-size:.86rem}}
th,td{{text-align:left;padding:9px 11px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-size:.7rem;text-transform:uppercase;color:var(--muted);background:var(--bg)}}td small{{display:block;color:var(--muted)}}
ul{{margin:0;padding-left:18px}}li small{{color:var(--muted)}}
.fr{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px}}
.fr span{{font-size:.8rem;padding:4px 8px;border-radius:999px}}.ok{{background:var(--pass-soft);color:var(--pass)}}.bad{{background:var(--fail-soft);color:var(--fail)}}
.lock{{display:flex;flex-wrap:wrap;gap:8px}}.lock span{{font-size:.82rem;padding:6px 10px;border-radius:999px;border:1px dashed var(--line);color:var(--muted)}}
svg.cv{{width:100%;max-width:420px;height:auto}}
</style>
<div class="w">
<div><div style="font:500 .72rem/1 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)">Viewer chain · {e(brand)} · {e(avatar)} · round {e(r.get("round"))}</div><h1>{e(title or "Viewer chain")}</h1></div>
<div class="ban">{"Worth making — it passed." if ok else "Not worth making yet — goes back to " + e(say(r.get("fix_at"))) + (" (around " + e(r.get("at")) + ")" if r.get("at") else "")}</div>
<section><h2>The numbers</h2><div class="g">{"".join(f'<div class="n"><b>{e(a)}</b><span>{e(b)}</span></div>' for a, b in nums)}</div>
{f'<svg class="cv" viewBox="0 0 {W} {Hh}"><polyline points="{pts}" fill="none" stroke="var(--accent)" stroke-width="2.5"/><text x="10" y="{Hh-1}" font-size="9" fill="var(--muted)">still watching, second by second</text></svg>' if curve else ""}</section>
{_changes_html(r)}<section><h2>Pass or fail</h2><div class="lts">{"".join(light(k, c) for k, c in checks.items())}</div></section>
{_belief_html(r)}<section><h2>The 5 viewers</h2><div class="vws">{viewers}</div></section>
<section><h2>Their doubts vs your objection bank</h2>{f'<div class="t"><table><thead><tr><th></th><th>They said</th><th>Bank objection</th><th>Bank answer (verbatim)</th></tr></thead><tbody>{matches}</tbody></table></div>' if matches else '<p style="color:var(--muted)">' + e(ob.get("skipped") or ob.get("error") or "nothing to match") + "</p>"}
{f"<h2>Comments likely under it</h2><ul>{likely}</ul>" if likely else ""}{f"<h2>New objections, not in the bank</h2><ul>{newob}</ul>" if newob else ""}</section>
<section><h2>Hidden by the app</h2>{fr or '<p style="color:var(--muted)">No frames yet. This runs once the storyboard frames or clips exist.</p>'}
<p style="font-size:.8rem;color:var(--muted)">Reels uses Meta's own numbers; ≈ means TikTok or Shorts, which are approximate.</p></section>
<section><h2>Waiting for install</h2><div class="lock"><span>🔒 Where do eyes go</span><span>🔒 Will they keep watching (from the real video)</span><span>🔒 What does the face show</span></div></section>
</div>"""


# ── the whole loop, one piece (the video chain, the statics chain and the
#    standalone runner all call this — the owner, 2026-10-03: "install this in the
#    actual process so we can start pumping out briefs") ────────────────────

def _passes(r: dict) -> int:
    return sum(1 for c in (r.get("checks") or {}).values() if c.get("passed"))


def run_loop(run, brand: str, avatar: str, text: str, kind: str = "video", sub: str | None = None,
             label: str = "", max_fix: int = 3, say=print) -> tuple[dict, str]:
    """check → (answers from real data → rewrite → check)… up to max_fix rewrites,
    never building on a worse version; a pass after a fail is learned.
    Returns the final result (with history and changes) and the final brief text."""
    run = Path(run)
    run.mkdir(parents=True, exist_ok=True)
    HAND_DEFAULT[0] = run / "hand"
    who = sub or avatar
    label = label or run.name
    (run / "brief-r0.md").write_text(text)
    history, changes, failed = [], [], []
    answered = set()
    r = check(run, brand, avatar, text, kind=kind, sub=sub, round_n=_next_round(run))
    history.append({"round": r["round"], "passed": r["passed"], "fix_at": r["fix_at"], "brief": "brief-r0.md"})
    best = (r, text)
    say(f"  round {r['round']}: " + ("passed" if r["passed"] else f"failed — {say(r['fix_at'])}"))
    for k in range(max_fix):
        if r["passed"] or r["fix_at"] == "audience":
            break
        failed.append(r)
        # Worries the bank can't answer get answered from real data first
        # (the owner, 2026-10-02: "everything needs to come from real data").
        new = (r.get("objections") or {}).get("new_objections") or []
        new = [w for w in new if w not in answered]
        if new:
            say(f"  finding real answers for {len(new)} new worr{'y' if len(new) == 1 else 'ies'} in the customers' own words…")
            try:
                fa = find_answers(brand, who, new, label=label)
                answered.update(new)
                got = sum(1 for x in fa.get("answers") or [] if x.get("found"))
                say(f"    answered {got} of {len(new)} from real data · {fa.get('dropped_unverified', 0)} unverified quotes dropped")
                r["notes"] = (r.get("notes") or "") + "\n\nReal answers found in the customers' own words (quote them only as written, as a quoted customer review):\n" + \
                    "\n".join(f"- {x.get('worry')}: " + " | ".join(f"\"{ln['quote']}\" ({ln.get('avatar')} {ln.get('who')})" for ln in (x.get("answer_lines") or [])[:3])
                              for x in fa.get("answers") or [] if x.get("found"))
            except Exception as e:
                say(f"    the answer search could not run ({type(e).__name__}: {str(e)[:100]})")
        say(f"  rewriting {say(r['fix_at'])} with the bank's answers and the customers' words…")
        try:
            text, ch = fix(text, r, brand, who)
        except ValueError as e:
            say(f"  rewrite refused: {str(e)[:140]} — trying once more, told why")
            try:
                text, ch = fix(text, r, brand, who, refused=str(e))
            except Exception as e2:
                say(f"  the rewrite could not be done inside the rules ({str(e2)[:120]}) — stopping here")
                break
        except Exception as e:
            say(f"  the rewrite could not run ({type(e).__name__}: {str(e)[:120]}) — stopping here")
            break
        n = len(history)
        (run / f"brief-r{n}.md").write_text(text)
        (run / f"changes-r{n}.json").write_text(json.dumps(ch, indent=1, ensure_ascii=False) + "\n")
        changes += ch.get("changes") or []
        r = check(run, brand, avatar, text, kind=kind, sub=sub, round_n=_next_round(run))
        history.append({"round": r["round"], "passed": r["passed"], "fix_at": r["fix_at"], "brief": f"brief-r{n}.md"})
        say(f"  round {r['round']}: " + ("passed" if r["passed"] else f"failed — {say(r['fix_at'])}")
              + f" · {_passes(r)} checks pass")
        # Never build on a worse version: the next rewrite starts from the best so far.
        if not r["passed"] and _passes(r) < _passes(best[0]):
            say(f"  that rewrite made it worse ({_passes(r)} vs {_passes(best[0])}) — the next one starts from round {best[0]['round']}")
            text = best[1]
            r_next = dict(best[0]); r_next["notes"] = (best[0].get("notes") or "") + \
                f"\n\nA previous rewrite made it WORSE. What it changed: " + "; ".join(f"{c.get('where')}: {c.get('now', '')[:80]}" for c in (ch.get("changes") or [])) + ". Don't repeat that."
            r = r_next
        elif _passes(r) >= _passes(best[0]):
            best = (r, text)
    if not r["passed"] and _passes(best[0]) > _passes(r):
        r, text = best[0], best[1]
    opens = []
    for f in sorted(run.glob("changes-r*.json")):
        try:
            opens += json.loads(f.read_text()).get("open") or []
        except Exception:
            pass
    for d in sorted((run / "viewer-check").glob("r*")):
        if (d / "objections.json").exists():
            opens += json.loads((d / "objections.json").read_text()).get("new_objections") or []
    nf = note_new_objections(brand, who, label, opens)
    if nf:
        say(f"  new objections with no answer on file: {nf}")
    if r["passed"] and failed:
        f = learn(brand, who, label, failed, r, changes)
        say(f"  learned: {f}")
    r["history"], r["changes"] = history, changes
    (run / "chain.json").write_text(json.dumps({"history": history, "changes": changes,
                                                "final_brief": next((h.get("brief") for h in history if h.get("round") == r.get("round")), "brief-r0.md")},
                                               indent=1, ensure_ascii=False) + "\n")
    return r, text


# ── one check ──────────────────────────────────────────────────────────────

def check(run_dir, brand: str, avatar: str, brief, kind: str = "video", sub: str | None = None,
          round_n: int = 1, handle: str | None = None, caller=None) -> dict:
    run_dir = Path(run_dir)
    USED.clear()
    out = run_dir / "viewer-check" / f"r{round_n}"
    out.mkdir(parents=True, exist_ok=True)
    if os.environ.get("QC_VIEWER", "1") == "0":
        return {"passed": True, "skipped": "QC_VIEWER=0"}
    who, card_file = card(brand, avatar, sub, caller=caller)
    fd = feed_dir(brand, avatar, sub)
    if not fd:
        raise FileNotFoundError(f"no avatar feed for {brand}/{sub or avatar} in {FEEDS}")
    # One cut per brief: every round of the SAME words reads the same thing,
    # so a pass or a fail is the viewers, never a re-translation.
    import hashlib
    btxt = Path(brief).read_text() if len(str(brief)) < 1000 and Path(str(brief)).exists() else str(brief)
    cache = run_dir / "viewer-check" / f"cut-{hashlib.md5((kind + btxt).encode()).hexdigest()[:10]}.json"
    if cache.exists():
        cut = json.loads(cache.read_text())
    else:
        cut = viewer_cut(btxt, kind, caller=caller)
        cache.write_text(json.dumps(cut, indent=1, ensure_ascii=False) + "\n")
    (out / "viewer-cut.json").write_text(json.dumps(cut, indent=1, ensure_ascii=False) + "\n")
    length_s = float(cut.get("length_s") or 0)
    tpl = newest("viewer-check").read_text()
    platform = "TikTok"
    answers, ours_at = [], []
    muted = [1, 3] if length_s else []         # 2 of 5 scroll with the sound off, as most people do
    sents = []
    for i in range(N_VIEWERS):
        seed = round_n * 100 + i
        posts = [post_text(x) for x in feed_posts(fd, seed)]
        at = random.Random(seed).randint(2, len(posts) + 1)
        posts.insert(at - 1, ours_text(cut, handle or brand))
        feed = "\n\n".join(f"--- POST {n} ---\n{p}" for n, p in enumerate(posts, 1))
        sent = (tpl.replace("{brand}", brand).replace("{avatar}", sub or avatar).replace("{who}", who)
                   .replace("{when}", WHENS[i % len(WHENS)]).replace("{platform}", platform)
                   .replace("{sound}", "Your sound is OFF: you hear nothing, so ignore every voice, sound and song line below — only what is on screen reaches you." if i in muted else "Your sound is on.")
                   .replace("{feed}", "## Your feed\n\n" + feed))
        (out / f"viewer-{i + 1}-sent.md").write_text(sent)
        sents.append(sent)
        ours_at.append(at)

    def one(sent):            # the 5 viewers scroll at the same time, each on their own
        try:
            return ask(sent, temperature=0.9, caller=caller)
        except ValueError:                      # an answer that can't be read gets one more go
            return ask(sent, temperature=0.9, caller=caller)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=N_VIEWERS) as pool:
        gots = list(pool.map(one, sents))
    for i, got in enumerate(gots):
        (out / f"viewer-{i + 1}-answer.json").write_text(json.dumps(got, indent=1, ensure_ascii=False) + "\n")
        if isinstance(got, list):              # some answers come back as the bare list
            got = {"posts": got}
        answers.append(got.get("posts") or [])
    (out / "key.json").write_text(json.dumps({"ours_at": ours_at, "feed": fd.name, "card": card_file.name}) + "\n")
    sc = score(answers, ours_at, length_s, cut.get("offer_at"), muted=muted, offer_set=offer_words(cut))
    try:
        bd = belief_drivers(cut, brand, caller=caller)
    except Exception as e:
        bd = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
    (out / "belief.json").write_text(json.dumps(bd, indent=1, ensure_ascii=False) + "\n")
    if "passed" in bd:
        # Belief is what real buyers said made them buy, given by the ad — not a
        # simulated viewer saying "yes". The viewers' own answer stays as information.
        if "believe" in sc["checks"]:
            sc["checks"]["viewers_believe"] = dict(sc["checks"].pop("believe"), passed=True, info=True)
        sc["checks"]["belief"] = {"value": f"gives {bd['given']} of the top {len(bd['themes'])} reasons real customers bought"
                                           + ("" if bd.get("proof") else " · no proof (real results or reviews)")
                                           + (f" · missing: {', '.join(bd['missing'][:3])}" if bd["missing"] else ""),
                                  "passed": bd["passed"]}
        sc["passed"] = all(c["passed"] for c in sc["checks"].values())
    # NEW TO META (the owner, 2026-10-08: "add in to the viewer … identifying diversity
    # against the scripts / briefs it reads"). Meta runs ads that "look or feel alike"
    # as one creative, so a brief that copies what's running — or a brief already
    # written — is sent back before a cent is spent. Read off the brief's words
    # (creative-diversity/brief_view.py); scored on the seven moves (check.py).
    dv = diversity(brand, btxt, run_dir)
    if dv:
        (out / "diversity.json").write_text(json.dumps(dv, indent=1, ensure_ascii=False) + "\n")
        if "error" not in dv:
            sc["checks"]["new_to_meta"] = {"value": dv["value"], "passed": dv["passed"]}
            sc["passed"] = all(c["passed"] for c in sc["checks"].values())
    ow = offer_words(cut)
    for m in sc["mine"]:
        if is_offer(m.get("pitch_line"), ow):
            m["_offer_pitch"] = True
    rt = route(sc, length_s)
    # only the new-to-Meta line failed: the brief goes back for its moves
    if dv and dv.get("passed") is False and all(c["passed"] for k, c in sc["checks"].items() if k != "new_to_meta"):
        rt = {"fix_at": "diversity", "at": None}
    ob = {}
    if any("believe" in p for p in sc["mine"]):
        try:
            ob = objections(sc["mine"], brand, sub or avatar, caller=caller)
        except Exception as e:
            ob = {"error": f"the objection match could not run ({type(e).__name__}: {str(e)[:120]})",
                  "bank_missing": bank_missing(brand)}
        (out / "objections.json").write_text(json.dumps(ob, indent=1, ensure_ascii=False) + "\n")
    notes = "" if sc["passed"] else writer_notes(sc, rt)
    if dv and not dv.get("passed", True):
        notes += ("\n\nNEW TO META: Meta runs ads that look or feel alike as one creative. " + dv["note"]
                  + " Change at least " + str(dv["need"]) + " of: who it's for, awareness, format, the lead person, "
                  "the setting, the look. Keep the offer, the core message and the words that work.")
    if notes and bd.get("missing"):
        ex = {t["theme"]: t for t in bd.get("themes") or []}
        notes += "\n\nWHY REAL CUSTOMERS BOUGHT, and this ad doesn't give it yet (from their answers to 'what gut instinct made you buy?'). " \
                 "Give these, from real data only; a real customer's line may go on screen as a quoted review:\n" + \
                 "\n".join(f"- {m} ({ex[m]['share']:.0%} of buyers) — e.g. " + " | ".join(f"\"{e['quote'][:150]}\" [{e['id']}]" for e in ex[m]["examples"][:3])
                           for m in bd["missing"] if m in ex)
    known = [m for m in ob.get("matches") or [] if m.get("answer") and m.get("answer") not in ("no answer on file",) and m.get("objection") != "not in the bank"]
    if notes and known:
        notes += "\n\nTheir doubts are ones the brand already has answers for. Answer them with the bank's own words, quoted, nothing new:\n" + \
                 "\n".join(f"- \"{m.get('said')}\" → bank: \"{m.get('objection')}\" ({m.get('where')}) → answer on file: \"{m.get('answer')}\"" for m in known)
    if notes and ob.get("new_objections"):
        notes += "\n\nNew worries the bank has no answer for (don't invent one — flag for the owner): " + "; ".join(ob["new_objections"])
    verdict = ["# Viewer check — round " + str(round_n), "",
               f"**{'PASSED' if sc['passed'] else 'FAILED — goes back to ' + say(rt['fix_at'])}**"
               + (f" (around {rt['at']})" if rt.get("at") else ""), "",
               f"Feed: `{fd.name}` · card: `{card_file.name}` · viewers: {N_VIEWERS} · models: {', '.join(sorted(USED)) or MODEL}", "",
               "| Check | Result | |", "|---|---|---|"]
    for k, c in sc["checks"].items():
        verdict.append(f"| {k.replace('_', ' ')} | {c['value']} | {'pass' if c['passed'] else 'FAIL'} |")
    verdict += ["", "## What they said about ours", ""]
    for i, p in enumerate(sc["mine"], 1):
        verdict.append(f"- **Viewer {i}** — stop {p.get('stop')}, left {p.get('left_at')}, ad at {p.get('ad_at')}, "
                       f"tap {p.get('tap')}. \"{p.get('felt', '')}\" · giveaway: \"{p.get('ad_tell', '')}\" · "
                       f"text a friend: \"{p.get('text_friend', '')}\""
                       + (f" · believe: {p.get('believe')} (\"{p.get('doubt', '')}\") · fake: {p.get('fake')} · pitch: {p.get('pitch')} · for me: {p.get('for_me')} · would: {p.get('do')}" if "believe" in p else ""))
    if notes:
        verdict += ["", notes]
    p = sc["predicted"]
    verdict += ["", "## Predicted numbers — a guess from the viewers, not yet checked against Meta", ""]
    if p.get("kind") == "video":
        verdict += [f"- Hook rate (still watching at 0:03): {p['hook_rate']:.0%} — the real posts around it: {p['feed_stop_rate']:.0%}",
                    f"- Average watch: {p['avg_watch_s']}s of {int(p['length_s'])}s ({p['avg_watch_pct']:.0%})",
                    (f"- Reach the offer at {int(p['offer_at'])}s: {p['reach_offer']:.0%}" if p.get("reach_offer") is not None else "- No offer found in the brief"),
                    f"- Would tap or tell a friend: {p['act_rate']:.0%}",
                    "- Still watching, second by second: " + " ".join(f"{int(x * 100)}" for x in p["retention"])]
        if "believe_rate" in p:
            verdict += [f"- Believe it would work for them (of those who stopped): {p['believe_rate']:.0%}",
                        f"- Would save {p['save_rate']:.0%} · share {p['share_rate']:.0%} · comment {p['comment_rate']:.0%}"]
    else:
        verdict += [f"- Stop rate: {p['stop_rate']:.0%} — the real posts around it: {p['feed_stop_rate']:.0%}",
                    f"- Would tap or tell a friend: {p['act_rate']:.0%}"]
    (out / "VERDICT.md").write_text("\n".join(verdict) + "\n")
    (run_dir / "viewer-check" / "STAMP.json").write_text(json.dumps(
        {"brief": brief_key(btxt), "passed": sc["passed"], "fix_at": rt["fix_at"], "round": round_n,
         "folder": str(out), "predicted": p, "checks": sc["checks"]}, indent=1) + "\n")
    try:
        from . import qc_log
        qc_log.add(run_dir, "viewer check", f"{N_VIEWERS} viewers ({MODEL})",
                   {"viewer-check": {"ok": sc["passed"], "severity": "none" if sc["passed"] else "BLOCKER",
                                     "problems": [] if sc["passed"] else
                                     [f"{k.replace('_', ' ')}: {c['value']}" for k, c in sc["checks"].items() if not c["passed"]],
                                     "fix_at": rt["fix_at"], "prompt_change": notes}},
                   method="the ad scrolled inside its avatar's real feed by 3 fresh viewers; scored in code against the real posts")
    except Exception:
        pass
    res = {"passed": sc["passed"], "checks": sc["checks"], "fix_at": rt["fix_at"], "at": rt["at"], "belief": bd,
           "notes": notes, "round": round_n, "folder": str(out), "predicted": p, "objections": ob, "mine": sc["mine"]}
    try:
        (out / "REPORT.html").write_text(report_html(res, brand, sub or avatar, title=Path(str(brief)).stem if len(str(brief)) < 1000 else ""))
    except Exception:
        pass
    return res
