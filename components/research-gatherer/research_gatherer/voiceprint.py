#!/usr/bin/env python3
"""voiceprint.py — the SPOKEN PROFILE of a brand's real creators, measured
off their own audio.

    python3 components/research-gatherer/gather.py voiceprint --brand B --creator H
    python3 components/research-gatherer/gather.py voiceprint --brand B --all
    python3 components/research-gatherer/gather.py voiceprint --brand B --all --dry-run

the owner's ruling (2026-09-19): "analyze our actual content creators that we've
worked with to get a real profile of the avatar and how they deliver
messaging — we have tons of good-quality creators we've done teardowns on;
analyze the audio specifically and create voice prints. Then we fine-tune
everything in ElevenLabs so we come out with truly human scripts and voices."

What it does, per creator, for every SELECTED post on the brand's creator
drive:

1. pulls the audio with ffmpeg (mono, 16 kHz wav) into a scratch folder;
2. transcribes it ONCE on ElevenLabs Scribe with word timestamps — the same
   door lineparity.py uses — and keeps the transcript in the creator's own
   folder (`transcripts/<post>.json`), so nothing is ever re-spent;
3. measures the SPOKEN PROFILE: words per minute · mean and median sentence
   length · fragment rate · contraction rate · filler and discourse-marker
   inventory · openers · sign-offs · questions per minute · pause profile ·
   energy (RMS and zero-crossing summary off the wav — no numpy) · the top
   in-words and phrases, each with one receipt (post id + timestamp);
4. writes `runs/research/<brand>/creators/<handle>/voiceprint.json` +
   `voiceprint.md` and the roll-up `runs/research/<brand>/creators/VOICEPRINTS.md`,
   keyed to
   the avatar and sub-avatar each creator's profile.md names.

Every number carries its denominator. Every phrase carries a receipt. The
transcript is the creator's own words and is never edited.

Agnostic: no brand, creator, avatar or room is named here. The brand comes
from `--brand`, the creators from the drive's own SELECTED file, the avatar
link from each profile.md's "Avatar fit" section matched against the
brand's own core-avatars folder. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import math
import mimetypes
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
import wave
from array import array
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORKSPACE = ROOT.parents[1]
sys.path.append(str(WORKSPACE / "components" / "brandpath"))   # appended, never ahead of this machine
import brandpath as BP  # noqa: E402

ELEVEN_STT = "https://api.elevenlabs.io/v1/speech-to-text"
STT_MODEL_ID = "scribe_v1"
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"   # found on PATH, never one Mac's Homebrew prefix
def _drive_mount():
    """The Google Drive mount holding the team's shared drive.

    Was hardcoded to one person's account, so it resolved to nothing on any
    other machine. DRIVE_ACCOUNT pins it; unset, the first GoogleDrive-*
    mount found is used.
    """
    import os
    cs = Path.home() / "Library/CloudStorage"
    acct = os.environ.get("DRIVE_ACCOUNT")
    if acct:
        return cs / f"GoogleDrive-{acct}"
    return next(iter(sorted(cs.glob("GoogleDrive-*"))), cs / "GoogleDrive")


def _drive_root():
    """VOICEPRINT_DRIVE_ROOT — the folder under the mount the drive's SELECTED
    file and creator folders sit in (a path relative to the mount, or absolute)."""
    import os
    rel = os.environ.get("VOICEPRINT_DRIVE_ROOT") or "Shared drives"
    return _drive_mount() / rel


DRIVE_ROOT = _drive_root()
MIN_PAUSE = 0.3          # seconds — a silence between two words that counts as a pause
MIN_WORDS = 8            # a post with fewer spoken words is music or a caption piece, not speech
THIN_WORDS = 100         # a creator under this many measured words is reported but flagged thin
RMS_WINDOW = 0.1         # seconds — the energy window

# Fillers and discourse markers, counted as whole tokens or phrases. This is
# a COUNTING list, not a style list: everything here is counted whether or
# not a room uses it, and the profile reports what it found. Multi-word
# entries are matched as phrases.
MARKERS = [
    "so", "look", "honestly", "i mean", "right", "you know", "okay", "ok",
    "like", "well", "anyway", "actually", "literally", "basically", "just",
    "um", "uh", "y'all", "listen", "guys", "girl", "girls", "seriously",
    "obviously", "kind of", "sort of", "you guys", "oh my gosh", "oh my god",
    "let me tell you", "here's the thing", "i'm not gonna lie", "not gonna lie",
    "trust me", "i promise", "i swear", "you're welcome", "hey", "hi",
    "alright", "all right", "now", "again", "at all", "i think", "i feel like",
    "to be honest", "let's", "come on", "no joke", "for real", "period",
]
CONTRACTION = re.compile(r"\b\w+['’](s|t|re|ve|ll|d|m)\b", re.I)
REDUCED = re.compile(r"\b(gonna|wanna|gotta|kinda|sorta|lemme|gimme|dunno|"
                     r"outta|ya|yall|y'all|cause|'cause|cuz)\b", re.I)
VERB_HINT = {
    "is", "am", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "can", "could", "will", "would", "should",
    "may", "might", "must", "get", "got", "gets", "go", "goes", "going",
    "went", "gone", "love", "loves", "loved", "want", "wants", "wanted",
    "need", "needs", "needed", "use", "uses", "used", "put", "puts", "think",
    "thought", "know", "knew", "see", "saw", "seen", "look", "looks",
    "looked", "try", "tried", "make", "makes", "made", "take", "takes",
    "took", "come", "comes", "came", "say", "says", "said", "tell", "told",
    "feel", "feels", "felt", "keep", "keeps", "kept", "let", "lets", "give",
    "gives", "gave", "find", "found", "start", "started", "stop", "stopped",
    "buy", "bought", "wear", "wore", "show", "showed", "work", "works",
    "worked", "help", "helps", "helped", "mean", "means", "meant", "call",
    "called", "run", "ran", "turn", "turned", "stay", "stayed", "leave",
    "left", "live", "lived", "watch", "watched", "wait", "waited", "let's",
    "gonna", "wanna", "gotta", "hate", "hated", "notice", "noticed", "apply",
    "applied", "rub", "scrub", "wash", "washed", "cover", "covered", "hide",
    "hid", "pay", "paid", "cost", "costs", "sit", "sat", "stand", "stood",
    "hold", "held", "swear", "promise", "guess", "bet", "care", "matter",
    "matters", "happen", "happened", "change", "changed", "grow", "grew",
    "fade", "faded", "spend", "spent", "order", "ordered", "share", "shared",
    "post", "posted", "check", "checked", "trust", "believe", "remember",
}
STOPWORDS = set("""
a an the and or but if so of to in on at by for with from as is am are was
were be been being have has had do does did can could will would should may
might must i me my mine you your yours he him his she her hers it its we us
our ours they them their theirs this that these those there here what which
who whom whose when where why how not no yes just very really too also then
than now out up down over under again all any some each every both few more
most other such only own same into about after before between through
during without within because while until once off than s t d ll re ve m
um uh oh like okay ok well right know mean thing things got get go going
gonna wanna one two three lot little bit way kind sort much many even still
ever never always back yeah yep nope hey hi
""".split())


# --------------------------------------------------------------- plumbing

def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def key_of() -> str | None:
    """ELEVENLABS_API_KEY — the Keychain vault through daemn_keys, never a
    plain-text file. None when it is not there."""
    import os
    k = os.environ.get("ELEVENLABS_API_KEY")
    if k:
        return k
    try:
        import daemn_keys
        return daemn_keys.key("ELEVENLABS_API_KEY") or None
    except Exception:
        return None


def _boundary() -> str:
    return f"----daemn-{uuid.uuid4().hex}"


def _multipart_body(fields: dict, files: list[tuple[str, Path]], boundary: str) -> bytes:
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                     f'{value}\r\n'.encode())
    for name, path in files:
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                     f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
                     + path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts)


def http_transport(method: str, url: str, headers: dict, body: bytes | None):
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def read_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text())


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


# --------------------------------------------------------------- the drive

def selected_file(drive_root: Path) -> Path | None:
    """The newest SELECTED-<date>.json on the creator drive."""
    folder = drive_root / "creators"
    if not folder.is_dir():
        return None
    files = sorted(folder.glob("SELECTED-*.json"))
    return files[-1] if files else None


def selected_posts(brand: str, drive_root: Path | None = None) -> dict[str, list[dict]]:
    """{handle: [{id, name, post, video: <absolute path>}]} for every ready
    video the drive's SELECTED file names for this brand. Empty when the
    drive is not mounted or the file names another brand."""
    root = drive_root or DRIVE_ROOT
    sf = selected_file(root)
    if not sf:
        return {}
    doc = read_json(sf, {}) or {}
    if doc.get("brand") and doc["brand"] != brand:
        return {}
    out: dict[str, list[dict]] = {}
    for handle, c in (doc.get("creators") or {}).items():
        vids = []
        for v in c.get("videos") or []:
            if not v.get("ready") or not v.get("video"):
                continue
            path = root / v["video"]
            vids.append(dict(id=v.get("id") or Path(v["video"]).parent.name,
                             name=v.get("name") or "", post=v.get("post") or "",
                             video=str(path), exists=path.is_file()))
        if vids:
            out[handle] = vids
    return out


# --------------------------------------------------------------- audio

def extract_wav(video: Path, out: Path, ffmpeg: str = FFMPEG) -> tuple[bool, str]:
    """(ok, why). A file with no audio stream is the common failure and is
    named as such rather than reported as a tool error."""
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video),
                        "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", str(out)],
                       capture_output=True, text=True)
    if r.returncode == 0 and out.is_file():
        return True, ""
    err = (r.stderr or "").strip()
    if "does not contain any stream" in err or "Output file #0 does not contain" in err:
        return False, "the file has no audio track"
    return False, err.splitlines()[-1][:120] if err else "ffmpeg failed"


def energy_profile(wav_path: Path) -> dict:
    """RMS in dBFS per window (mean, spread, loud-window share) and the mean
    zero-crossing rate — a cheap stand-in for pitch and energy, no numpy.
    Every figure names its window count."""
    try:
        with wave.open(str(wav_path), "rb") as w:
            rate, n = w.getframerate(), w.getnframes()
            width = w.getsampwidth()
            raw = w.readframes(n)
    except Exception:
        return {}
    if width != 2 or not raw:
        return {}
    samples = array("h")
    samples.frombytes(raw)
    win = max(1, int(rate * RMS_WINDOW))
    rms_db, zcr = [], []
    for i in range(0, len(samples) - win + 1, win):
        chunk = samples[i:i + win]
        acc = 0
        zc = 0
        prev = chunk[0]
        for s in chunk:
            acc += s * s
            if (s >= 0) != (prev >= 0):
                zc += 1
            prev = s
        rms = math.sqrt(acc / win)
        rms_db.append(20 * math.log10(rms / 32768.0) if rms > 0 else -96.0)
        zcr.append(zc / win)
    if not rms_db:
        return {}
    voiced = [d for d in rms_db if d > -40.0]
    return {
        "windows": len(rms_db),
        "window_s": RMS_WINDOW,
        "rms_dbfs_mean": round(statistics.fmean(rms_db), 1),
        "rms_dbfs_voiced_mean": round(statistics.fmean(voiced), 1) if voiced else None,
        "rms_dbfs_spread": round(statistics.pstdev(rms_db), 1),
        "voiced_share": round(len(voiced) / len(rms_db), 3),
        "zcr_mean": round(statistics.fmean(zcr), 4),
        "zcr_spread": round(statistics.pstdev(zcr), 4),
        "duration_s": round(len(samples) / rate, 2),
    }


# --------------------------------------------------------------- scribe

def transcribe(wav_path: Path, key: str | None, transport=None, dry_run: bool = False) -> dict | None:
    """One Scribe call with word timestamps. Returns the raw response
    (`text`, `words[]` with start/end/type). None on a dry run."""
    transport = transport or http_transport
    boundary = _boundary()
    fields = {"model_id": STT_MODEL_ID, "timestamps_granularity": "word",
              "diarize": "false", "tag_audio_events": "true"}
    headers = {"xi-api-key": key or "",
               "Content-Type": f"multipart/form-data; boundary={boundary}"}
    if dry_run:
        print(json.dumps({"method": "POST", "url": ELEVEN_STT, "fields": fields,
                          "file": str(wav_path)}, indent=1))
        return None
    body = _multipart_body(fields, [("file", wav_path)], boundary)
    status, _h, resp = transport("POST", ELEVEN_STT, headers, body)
    data = json.loads(resp.decode()) if resp else {}
    if status is not None and status >= 400:
        raise RuntimeError(f"ElevenLabs speech-to-text error {status}: {json.dumps(data)[:400]}")
    return data


def words_of(transcript: dict) -> list[dict]:
    """The spoken words in order — Scribe's `words[]` minus spacing and
    audio-event rows — each {text, start, end}."""
    out = []
    for w in transcript.get("words") or []:
        if (w.get("type") or "word") != "word":
            continue
        t = (w.get("text") or "").strip()
        if not t:
            continue
        out.append({"text": t, "start": float(w.get("start") or 0.0),
                    "end": float(w.get("end") or 0.0)})
    return out


# --------------------------------------------------------------- measuring

def _norm(tok: str) -> str:
    return re.sub(r"^[^\w'’]+|[^\w'’]+$", "", tok.lower()).replace("’", "'")


def sentences_of(text: str) -> list[str]:
    parts = re.split(r"(?<=[.?!])\s+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def is_fragment(sentence: str) -> bool:
    """Heuristic: no verb form detected, or three words or fewer. Named as a
    heuristic in the output so nobody reads it as parsing."""
    toks = [_norm(t) for t in sentence.split()]
    toks = [t for t in toks if t]
    if len(toks) <= 3:
        return True
    for t in toks:
        base = t.split("'")[0]
        if t in VERB_HINT or base in VERB_HINT:
            return False
        if re.search(r"(ing|ed)$", t) and len(t) > 4:
            return False
        if re.search(r"'(s|re|ve|ll|d|m)$", t) or t.endswith("n't"):
            return False
    return True


def marker_counts(text: str) -> dict[str, int]:
    low = " " + re.sub(r"[^\w'’ ]+", " ", text.lower().replace("’", "'")) + " "
    low = re.sub(r"\s+", " ", low)
    out = {}
    for m in MARKERS:
        n = low.count(f" {m} ")
        if n:
            out[m] = n
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def ngram_receipts(words: list[dict], n: int, post_id: str) -> dict[str, dict]:
    """{phrase: {count, receipt}} over the word list, stopword-only phrases
    skipped, one receipt (post + timestamp of the first occurrence)."""
    toks = [(_norm(w["text"]), w["start"]) for w in words]
    toks = [(t, s) for t, s in toks if t]
    out: dict[str, dict] = {}
    for i in range(len(toks) - n + 1):
        gram = toks[i:i + n]
        ws = [g[0] for g in gram]
        if all(w in STOPWORDS for w in ws):
            continue
        if n == 1 and (ws[0] in STOPWORDS or len(ws[0]) < 3 or ws[0].isdigit()):
            continue
        key = " ".join(ws)
        if key not in out:
            out[key] = {"count": 0, "receipt": f"{post_id} @ {gram[0][1]:.1f}s"}
        out[key]["count"] += 1
    return out


def measure_post(post: dict, transcript: dict, energy: dict) -> dict:
    words = words_of(transcript)
    # the text is built from the WORD rows: Scribe's own `text` carries the
    # audio-event tags ([laughs], [music]) inline, and those are not speech
    text = " ".join(w["text"] for w in words).strip()
    n_words = len(words)
    span = (words[-1]["end"] - words[0]["start"]) if n_words >= 2 else 0.0
    minutes = span / 60.0 if span > 0 else 0.0
    sents = sentences_of(text)
    lens = [len([t for t in s.split() if _norm(t)]) for s in sents]
    frags = [s for s in sents if is_fragment(s)]
    toks = [_norm(t) for t in text.split()]
    toks = [t for t in toks if t]
    contractions = len(CONTRACTION.findall(text)) + len(REDUCED.findall(text))
    pauses = []
    for a, b in zip(words, words[1:]):
        gap = b["start"] - a["end"]
        if gap >= MIN_PAUSE:
            pauses.append(round(gap, 2))
    questions = text.count("?")
    opener = " ".join(w["text"] for w in words[:5])
    signoff = " ".join(w["text"] for w in words[-5:])
    return {
        "post": post["id"], "name": post.get("name", ""), "url": post.get("post", ""),
        "words": n_words, "speech_span_s": round(span, 2),
        "wpm": round(n_words / minutes, 1) if minutes else None,
        "sentences": len(sents),
        "sentence_len_mean": round(statistics.fmean(lens), 1) if lens else None,
        "sentence_len_median": statistics.median(lens) if lens else None,
        "fragments": len(frags),
        "fragment_examples": frags[:3],
        "contractions": contractions, "tokens": len(toks),
        "markers": marker_counts(text),
        "opener": opener, "signoff": signoff,
        "questions": questions,
        "pauses": {"count": len(pauses), "mean_s": round(statistics.fmean(pauses), 2) if pauses else None,
                   "max_s": max(pauses) if pauses else None, "min_pause_s": MIN_PAUSE},
        "energy": energy,
        "unigrams": ngram_receipts(words, 1, post["id"]),
        "bigrams": ngram_receipts(words, 2, post["id"]),
        "trigrams": ngram_receipts(words, 3, post["id"]),
        "text": text,
    }


def _merge_grams(posts: list[dict], key: str, top: int) -> list[dict]:
    acc: dict[str, dict] = {}
    for p in posts:
        for phrase, row in (p.get(key) or {}).items():
            if phrase not in acc:
                acc[phrase] = {"phrase": phrase, "count": 0, "posts": 0, "receipt": row["receipt"]}
            acc[phrase]["count"] += row["count"]
            acc[phrase]["posts"] += 1
    rows = sorted(acc.values(), key=lambda r: (-r["posts"], -r["count"], r["phrase"]))
    return rows[:top]


def roll_up(handle: str, posts: list[dict]) -> dict:
    """One creator's spoken profile across every measured post, every figure
    with its denominator."""
    total_words = sum(p["words"] for p in posts)
    total_span = sum(p["speech_span_s"] for p in posts)
    total_sents = sum(p["sentences"] for p in posts)
    total_frags = sum(p["fragments"] for p in posts)
    total_tokens = sum(p["tokens"] for p in posts)
    total_contr = sum(p["contractions"] for p in posts)
    total_q = sum(p["questions"] for p in posts)
    pause_n = sum(p["pauses"]["count"] for p in posts)
    pause_means = [(p["pauses"]["mean_s"], p["pauses"]["count"]) for p in posts if p["pauses"]["mean_s"]]
    pause_mean = (sum(m * n for m, n in pause_means) / sum(n for _, n in pause_means)) if pause_means else None
    all_lens = []
    for p in posts:
        for s in sentences_of(p["text"]):
            all_lens.append(len([t for t in s.split() if _norm(t)]))
    markers: Counter = Counter()
    for p in posts:
        markers.update(p["markers"])
    minutes = total_span / 60.0 if total_span else 0.0
    energies = [p["energy"] for p in posts if p.get("energy")]

    def emean(k):
        vals = [e[k] for e in energies if e.get(k) is not None]
        return round(statistics.fmean(vals), 3) if vals else None

    return {
        "creator": handle,
        "measured": now(),
        "posts": [p["post"] for p in posts],
        "denominators": {"posts": len(posts), "words": total_words,
                         "speech_seconds": round(total_span, 1),
                         "sentences": total_sents, "tokens": total_tokens},
        "totals": {"fragments": total_frags, "contractions": total_contr,
                   "questions": total_q, "pauses": pause_n,
                   "sentence_words": sum(all_lens)},
        "thin": total_words < THIN_WORDS,
        "wpm": round(total_words / minutes, 1) if minutes else None,
        "sentence_len_mean": round(statistics.fmean(all_lens), 1) if all_lens else None,
        "sentence_len_median": statistics.median(all_lens) if all_lens else None,
        "fragment_rate": round(total_frags / total_sents, 3) if total_sents else None,
        "fragment_rule": "heuristic: no verb form detected, or three words or fewer",
        "contraction_rate_per_100_tokens": round(100 * total_contr / total_tokens, 2) if total_tokens else None,
        "markers_per_1000_words": {m: round(1000 * n / total_words, 2) for m, n in markers.most_common(25)} if total_words else {},
        "markers_count": dict(markers.most_common(25)),
        "openers": [{"post": p["post"], "words": p["opener"]} for p in posts],
        "signoffs": [{"post": p["post"], "words": p["signoff"]} for p in posts],
        "questions_per_minute": round(total_q / minutes, 2) if minutes else None,
        "questions": total_q,
        "pauses": {"per_minute": round(pause_n / minutes, 2) if minutes else None,
                   "count": pause_n, "mean_s": round(pause_mean, 2) if pause_mean else None,
                   "max_s": max([p["pauses"]["max_s"] or 0 for p in posts] or [0]),
                   "min_pause_s": MIN_PAUSE},
        "energy": {"rms_dbfs_voiced_mean": emean("rms_dbfs_voiced_mean"),
                   "rms_dbfs_spread": emean("rms_dbfs_spread"),
                   "voiced_share": emean("voiced_share"),
                   "zcr_mean": emean("zcr_mean"), "zcr_spread": emean("zcr_spread"),
                   "posts_measured": len(energies)},
        "in_words": _merge_grams(posts, "unigrams", 15),
        "phrases": _merge_grams(posts, "bigrams", 10) + _merge_grams(posts, "trigrams", 10),
        "per_post": [{k: v for k, v in p.items() if k not in ("unigrams", "bigrams", "trigrams", "text")}
                     for p in posts],
    }


# --------------------------------------------------------------- brand side

def creators_root(brand: str, root: Path | None = None) -> Path:
    """The creators' ROSTER — `profile.md` per handle. Brand truth, curated by
    people; this machine only ever READS it."""
    # brands/<brand>/content-creators (was creators/) — the folder plan's name,
    # resolved by brandpath so a rename never strands this reader again
    return BP.brand_path(brand, "content-creators", root=(root or WORKSPACE) / "brands")


def research_root(brand: str, root: Path | None = None) -> Path:
    """Where this machine's own output lives — transcripts, per-creator
    voiceprints and the brand roll-up. the owner ruled 2026-09-21 "all research
    should live in the research component moving forward"; the phase-1 rule
    (runs/README.md) keeps a machine's record under `runs/<machine>/<brand>/`
    and out of `brands/`, which is read-only to machines. 65 <brand> files
    moved here from `brands/<brand>/creators/` at that ruling."""
    return (root or WORKSPACE) / "runs" / "research" / brand / "creators"


def avatar_slugs(brand: str, root: Path | None = None) -> tuple[list[str], dict[str, list[str]]]:
    """The brand's own core-avatar slugs and each one's sub-avatar slugs,
    read off the folder — never named in code."""
    base = (root or WORKSPACE) / "brands" / brand / "core-avatars"
    cores, subs = [], {}
    if not base.is_dir():
        return cores, subs
    for d in sorted(base.iterdir()):
        if d.is_dir() and (d / "profile.md").is_file():
            cores.append(d.name)
            subs[d.name] = []
            sd = d / "sub-avatars"
            if sd.is_dir():
                for f in sorted(sd.glob("*.md")):
                    stem = re.sub(r"^sub-\d+-", "", f.stem)
                    subs[d.name].append(stem)
    return cores, subs


def avatar_fit(brand: str, handle: str, root: Path | None = None) -> dict:
    """{core, sub, line} from the creator's profile.md "Avatar fit" section,
    matched against the brand's own avatar and sub-avatar slugs."""
    pf = creators_root(brand, root) / handle / "profile.md"
    if not pf.is_file():
        return {"core": None, "sub": None, "line": "no profile.md"}
    text = pf.read_text()
    m = re.search(r"^## Avatar fit\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    block = m.group(1) if m else text
    cores, subs = avatar_slugs(brand, root)
    core = next((c for c in cores if re.search(r"\b" + re.escape(c) + r"\b", block)), None)
    sub = None
    if core:
        # "Sub-avatar: none" wins over a leaning mentioned later in the block
        first = re.search(r"sub-avatar[^\n]*", block, re.I)
        if first and re.search(r"\bnone\b", first.group(0), re.I):
            sub = None
        else:
            sub = next((s for s in subs.get(core, []) if re.search(r"\b" + re.escape(s) + r"\b", block)), None)
    line = ""
    m2 = re.search(r"\*\*Core:[^\n]*", block)
    if m2:
        line = re.sub(r"\*\*", "", m2.group(0)).strip()
    return {"core": core, "sub": sub, "line": line}


# --------------------------------------------------------------- rendering

def render_md(vp: dict, fit: dict) -> str:
    d = vp["denominators"]
    L = [f"# {vp['creator']} — voiceprint",
         "",
         f"Measured {vp['measured']} off {d['posts']} selected post(s): {d['words']} words over "
         f"{d['speech_seconds']} s of speech, {d['sentences']} sentences. Every figure below names "
         "its denominator; every phrase carries one receipt (post @ seconds). The transcripts are in "
         "`transcripts/` beside this file and are never edited.",
         "",
         f"Avatar fit (from profile.md): core `{fit.get('core') or 'unknown'}` · sub-avatar "
         f"`{fit.get('sub') or 'none'}`" + (f" — {fit['line']}" if fit.get("line") else ""),
         "",
         "## Rhythm",
         "",
         "| Measure | Value | Denominator |",
         "|---|---|---|",
         f"| Words per minute | {vp['wpm']} | {d['words']} words / {d['speech_seconds']} s |",
         f"| Sentence length, mean | {vp['sentence_len_mean']} words | {d['sentences']} sentences |",
         f"| Sentence length, median | {vp['sentence_len_median']} words | {d['sentences']} sentences |",
         f"| Fragment rate | {vp['fragment_rate']} | {d['sentences']} sentences ({vp['fragment_rule']}) |",
         f"| Contractions per 100 tokens | {vp['contraction_rate_per_100_tokens']} | {d['tokens']} tokens |",
         f"| Questions per minute | {vp['questions_per_minute']} | {vp['questions']} questions / {d['speech_seconds']} s |",
         f"| Pauses per minute (≥{vp['pauses']['min_pause_s']} s) | {vp['pauses']['per_minute']} | {vp['pauses']['count']} pauses / {d['speech_seconds']} s |",
         f"| Pause length, mean / max | {vp['pauses']['mean_s']} s / {vp['pauses']['max_s']} s | {vp['pauses']['count']} pauses |",
         "",
         "## Energy (off the wav, 100 ms windows)",
         "",
         "| Measure | Value |",
         "|---|---|",
         f"| Voiced level, mean | {vp['energy']['rms_dbfs_voiced_mean']} dBFS |",
         f"| Level spread | {vp['energy']['rms_dbfs_spread']} dB |",
         f"| Voiced share of windows | {vp['energy']['voiced_share']} |",
         f"| Zero-crossing rate, mean / spread | {vp['energy']['zcr_mean']} / {vp['energy']['zcr_spread']} |",
         "",
         "## Fillers and discourse markers (per 1000 words)",
         "",
         "| Marker | Per 1000 words | Count |",
         "|---|---|---|"]
    for m, r in vp["markers_per_1000_words"].items():
        L.append(f"| {m} | {r} | {vp['markers_count'][m]} |")
    L += ["", "## Openers (first five words of each post)", ""]
    for o in vp["openers"]:
        L.append(f"- {o['post']}: \"{o['words']}\"")
    L += ["", "## Sign-offs (last five words of each post)", ""]
    for o in vp["signoffs"]:
        L.append(f"- {o['post']}: \"{o['words']}\"")
    L += ["", "## In-words (top single words, stopwords removed)", "",
          "| Word | Posts | Count | Receipt |", "|---|---|---|---|"]
    for r in vp["in_words"]:
        L.append(f"| {r['phrase']} | {r['posts']} | {r['count']} | {r['receipt']} |")
    L += ["", "## Phrases (bigrams and trigrams)", "",
          "| Phrase | Posts | Count | Receipt |", "|---|---|---|---|"]
    for r in vp["phrases"]:
        L.append(f"| {r['phrase']} | {r['posts']} | {r['count']} | {r['receipt']} |")
    if vp.get("left_out"):
        L += ["", "## Left out", ""]
        for r in vp["left_out"]:
            L.append(f"- {r['post']}: {r['why']}")
    L += ["", "## Per post", "",
          "| Post | Words | WPM | Sentences | Fragments | Questions | Pauses | Opener |",
          "|---|---|---|---|---|---|---|---|"]
    for p in vp["per_post"]:
        L.append(f"| {p['post']} | {p['words']} | {p['wpm']} | {p['sentences']} | {p['fragments']} | "
                 f"{p['questions']} | {p['pauses']['count']} | \"{p['opener']}\" |")
    return "\n".join(L) + "\n"


def render_rollup(brand: str, rows: list[dict]) -> str:
    """VOICEPRINTS.md — every creator on one page, keyed to avatar and sub."""
    L = [f"# {brand} — creator voiceprints",
         "",
         "The SPOKEN PROFILE of every creator this brand has selected posts for, measured off "
         "their own audio (ElevenLabs Scribe, word timestamps; energy off the wav). One row per "
         "creator, keyed to the avatar and sub-avatar the creator's profile.md names. Each "
         "creator's own `voiceprint.md` carries the receipts.",
         "",
         f"Measured {now()}.",
         "",
         "| Creator | Core avatar | Sub-avatar | Posts | Words | WPM | Sent. mean / median | "
         "Fragments | Contr. /100 | Q /min | Pauses /min (mean s) | Top markers /1000 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        vp, fit = r["vp"], r["fit"]
        d = vp["denominators"]
        top = ", ".join(f"{m} {v}" for m, v in list(vp["markers_per_1000_words"].items())[:5])
        L.append(f"| {vp['creator']} | {fit.get('core') or 'unknown'} | {fit.get('sub') or 'none'} | "
                 f"{d['posts']} | {d['words']} | {vp['wpm']} | {vp['sentence_len_mean']} / "
                 f"{vp['sentence_len_median']} | {vp['fragment_rate']} | "
                 f"{vp['contraction_rate_per_100_tokens']} | {vp['questions_per_minute']} | "
                 f"{vp['pauses']['per_minute']} ({vp['pauses']['mean_s']}) | {top} |")
    # per-avatar band — POOLED BY DENOMINATOR, never a mean of creator means:
    # a creator measured on 27 words does not weigh what one measured on
    # 1,185 does. Thin creators (under THIN_WORDS) are listed but kept out
    # of the band's figures.
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["fit"].get("core") or "unknown", []).append(r["vp"])
    L += ["", "## By avatar — the band our own creators measured", "",
          f"Pooled by denominator across the creators the profile.md files map to each avatar. "
          f"A creator under {THIN_WORDS} measured words is listed as thin and left out of the figures.", ""]
    for core, vps in by.items():
        full = [v for v in vps if not v.get("thin")]
        thin = [v for v in vps if v.get("thin")]
        w = sum(v["denominators"]["words"] for v in full)
        s = sum(v["denominators"]["speech_seconds"] for v in full)
        sents = sum(v["denominators"]["sentences"] for v in full)
        toks = sum(v["denominators"]["tokens"] for v in full)
        tot = {k: sum((v.get("totals") or {}).get(k, 0) for v in full)
               for k in ("fragments", "contractions", "questions", "pauses", "sentence_words")}
        medians = [v["sentence_len_median"] for v in full if v["sentence_len_median"] is not None]
        markers: Counter = Counter()
        for v in full:
            markers.update(v["markers_count"])
        L.append(f"### `{core}` — {len(full)} creator(s) in the band"
                 + (f", {len(thin)} thin" if thin else "") + f": {w} words / {round(s, 1)} s / {sents} sentences")
        L.append("")
        L.append(f"- creators in the band: " + ", ".join(v["creator"] for v in full)
                 + (f" · thin: " + ", ".join(f"{v['creator']} ({v['denominators']['words']} words)" for v in thin) if thin else ""))
        L.append(f"- words per minute: {round(w / (s / 60), 1) if s else None} ({w} words / {round(s, 1)} s)")
        L.append(f"- sentence length, mean: {round(tot['sentence_words'] / sents, 1) if sents else None} words "
                 f"({tot['sentence_words']} words / {sents} sentences); creator medians "
                 f"{min(medians) if medians else None}–{max(medians) if medians else None}")
        L.append(f"- fragment rate: {round(tot['fragments'] / sents, 3) if sents else None} "
                 f"({tot['fragments']} / {sents} sentences; heuristic)")
        L.append(f"- contractions per 100 tokens: {round(100 * tot['contractions'] / toks, 2) if toks else None} "
                 f"({tot['contractions']} / {toks} tokens)")
        L.append(f"- pauses per minute (≥{MIN_PAUSE} s): {round(tot['pauses'] / (s / 60), 2) if s else None} "
                 f"({tot['pauses']} pauses); questions per minute: {round(tot['questions'] / (s / 60), 2) if s else None} "
                 f"({tot['questions']} questions)")
        L.append("- markers per 1000 words, pooled: " + (", ".join(
            f"{m} {round(1000 * n / w, 1)}" for m, n in markers.most_common(12)) if w else "none"))
        L.append("")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------- the run

def run_creator(brand: str, handle: str, posts: list[dict], key: str | None,
                dry_run: bool = False, transport=None, root: Path | None = None,
                scratch: Path | None = None, ffmpeg: str = FFMPEG) -> dict | None:
    home = research_root(brand, root) / handle
    tdir = home / "transcripts"
    scratch = scratch or Path(tempfile.mkdtemp(prefix="voiceprint-"))
    measured = []
    left_out: list[dict] = []
    spent = 0
    for p in posts:
        if not p.get("exists"):
            print(f"  {p['id']}: video not on the drive — skipped ({p['video']})")
            continue
        wav = scratch / handle / f"{p['id']}.wav"
        tfile = tdir / f"{p['id']}.json"
        ok, why = extract_wav(Path(p["video"]), wav, ffmpeg)
        if not ok:
            print(f"  {p['id']}: no audio to profile — {why}")
            left_out.append({"post": p["id"], "why": why})
            continue
        energy = energy_profile(wav)
        tr = read_json(tfile)
        if tr is None:
            if dry_run:
                print(f"  {p['id']}: would transcribe ({round(energy.get('duration_s') or 0, 1)} s)")
                transcribe(wav, key, dry_run=True)
                continue
            if not key:
                raise SystemExit("no ELEVENLABS_API_KEY in the Keychain vault — nothing transcribed")
            tr = transcribe(wav, key, transport=transport)
            tr = dict(tr or {}, _meta={"post": p["id"], "url": p.get("post"), "video": p["video"],
                                       "model": STT_MODEL_ID, "at": now()})
            write_json(tfile, tr)
            spent += 1
            print(f"  {p['id']}: transcribed ({len(words_of(tr))} words)")
        else:
            print(f"  {p['id']}: transcript on file ({len(words_of(tr))} words)")
        if len(words_of(tr)) < MIN_WORDS:
            print(f"  {p['id']}: {len(words_of(tr))} spoken word(s) — no speech to profile, left out")
            left_out.append({"post": p["id"], "why": f"{len(words_of(tr))} spoken word(s) — music or caption piece"})
            continue
        measured.append(measure_post(p, tr, energy))
    if not measured:
        return None
    vp = roll_up(handle, measured)
    vp["left_out"] = left_out
    vp["transcriptions_spent_this_run"] = spent
    fit = avatar_fit(brand, handle, root)
    vp["avatar_fit"] = fit
    write_json(home / "voiceprint.json", vp)
    (home / "voiceprint.md").write_text(render_md(vp, fit))
    return vp


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the spoken profile of a brand's creators, off their own audio")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--creator", help="one handle")
    ap.add_argument("--all", action="store_true", help="every creator with selected posts")
    ap.add_argument("--dry-run", action="store_true", help="extract and measure energy; transcribe nothing")
    ap.add_argument("--drive-root", default=str(DRIVE_ROOT))
    ap.add_argument("--workspace", default=str(WORKSPACE))
    a = ap.parse_args(argv)
    root = Path(a.workspace)
    sel = selected_posts(a.brand, Path(a.drive_root))
    if not sel:
        print(f"no SELECTED file for {a.brand} under {a.drive_root}/creators — is the drive mounted?")
        return 1
    handles = [a.creator] if a.creator else (sorted(sel) if a.all else [])
    if not handles:
        print("name --creator H or pass --all"); return 2
    key = None if a.dry_run else key_of()
    rows = []
    for h in handles:
        posts = sel.get(h)
        if not posts:
            print(f"{h}: no selected posts on the drive — skipped"); continue
        print(f"== {h}: {len(posts)} selected post(s)")
        vp = run_creator(a.brand, h, posts, key, dry_run=a.dry_run, root=root)
        if vp:
            rows.append({"vp": vp, "fit": vp["avatar_fit"]})
            print(f"   wpm {vp['wpm']} · sentences {vp['sentence_len_mean']}/{vp['sentence_len_median']} · "
                  f"fragments {vp['fragment_rate']} · contractions/100 {vp['contraction_rate_per_100_tokens']} · "
                  f"pauses/min {vp['pauses']['per_minute']}")
    # the roll-up reads EVERY voiceprint.json on file, so a single-creator run
    # still refreshes the brand page rather than shrinking it to one row
    all_rows = []
    vroot = research_root(a.brand, root)
    for d in (sorted(vroot.iterdir()) if vroot.is_dir() else []):
        f = d / "voiceprint.json"
        if f.is_file():
            vp = read_json(f)
            all_rows.append({"vp": vp, "fit": vp.get("avatar_fit") or avatar_fit(a.brand, d.name, root)})
    if all_rows and not a.dry_run:
        out = research_root(a.brand, root) / "VOICEPRINTS.md"
        out.write_text(render_rollup(a.brand, all_rows))
        print(f"\nroll-up: {out} ({len(all_rows)} creators)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
