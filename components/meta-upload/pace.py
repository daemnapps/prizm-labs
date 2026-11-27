"""pace — the uploader moves like a person, not a script (owner, 21 Oct 2026).

Three things, all set in pace.json:

* **Breathing room.** A short random pause between the pieces of one video, a longer one between videos, and a
  long one between ads, so a batch never arrives as one burst.
* **An hourly budget.** No more than `per_hour.bytes` sent and `per_hour.videos` videos in any rolling hour; past it
  the uploader waits until the hour frees up. Counted in runs/meta-upload/<brand>/pace.jsonl, so the budget holds
  across ads, retries and a restarted approve page.
* **Busy means wait, not quit.** A 5xx from Meta, or one of Meta's own "slow down / try again" error codes, waits
  (45 s, 2 min, 5 min, 10 min, each with a little jitter) and tries the same call again. Only after the last wait
  does it stop, and the upload resumes from upload-state.json on retry.

* **Meta's own meters.** Every reply's usage headers (x-business-use-case-usage, x-ad-account-usage, x-app-usage)
  are read (note_usage); before the next call the uploader slows as the top meter climbs past usage.slow_at %, and
  past usage.pause_at % (or when Meta names a time to regain access) waits that out (before_call). So a batch slows
  down before Meta's limit instead of failing on it (11 Nov 2026: code 17 / 2446079 on development access).

`META_PACE=off` turns every wait off (tests only)."""
import json, os, random, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CFG = json.loads((HERE / "pace.json").read_text())


def off():
    return os.environ.get("META_PACE") == "off"


def _sleep(lo_hi, why, log=None):
    if off():
        return 0
    s = random.uniform(*lo_hi)
    if log:
        log(f"  pace: {why}, {s:.0f} s")
    time.sleep(s)
    return s


def between_chunks(log=None):
    return _sleep(CFG["between_chunks_s"], "between pieces")


def between_videos(log=None):
    return _sleep(CFG["between_videos_s"], "between videos", log)


def between_ads(log=None):
    return _sleep(CFG["between_ads_s"], "between ads", log)


def _log_file(brand):
    if os.environ.get("META_RUNS_ROOT") or os.environ.get("META_CARDS_ROOT"):
        # a scratch tree (tests, fake trials) counts in its own runs home, never the real one (2026-10-27)
        import upload as U
        return U.brand_runs(brand) / Path(CFG["log"]).name
    return REPO / CFG["log"].replace("<brand>", brand)


def _recent(brand, now=None):
    now = now or time.time()
    f = _log_file(brand)
    rows = []
    if f.is_file():
        for line in f.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if now - r.get("t", 0) < 3600:
                rows.append(r)
    return rows


def budget_wait(brand, size, log=None, now=None):
    """Seconds to wait before a video of `size` bytes fits the rolling hour (0 = go now)."""
    if off():
        return 0
    now = now or time.time()
    rows = _recent(brand, now)
    cap = CFG["per_hour"]
    rows = [r for r in rows if not r.get("card_done")]
    for r in rows:                         # a video Meta fetched by link sent no bytes from here (pace.json _per_hour_link)
        if r.get("via") == "link":
            r["bytes"] = 0
    sent, n = sum(r.get("bytes", 0) for r in rows), len(rows)
    if sent + size <= cap["bytes"] and n + 1 <= cap["videos"]:
        return 0
    # wait until enough of the hour's sends have aged out
    rows.sort(key=lambda r: r["t"])
    for i, r in enumerate(rows):
        rest = rows[i + 1:]
        if sum(x.get("bytes", 0) for x in rest) + size <= cap["bytes"] and len(rest) + 1 <= cap["videos"]:
            return max(0, r["t"] + 3600 - now) + 5
    return 3605


def before_video(brand, size, log=None):
    w = budget_wait(brand, size, log)
    if w:
        if log:
            log(f"  pace: the hour's upload budget is used, waiting {w / 60:.0f} min")
        time.sleep(w)


def before_card(brand, log=None):
    """A gap since the last ad this brand finished uploading (pace.json between_ads), so ads never arrive back to back."""
    if off():
        return 0
    last = max((r["t"] for r in _recent(brand) if r.get("card_done")), default=None)
    if last is None:
        return 0
    want = random.uniform(*CFG["between_ads_s"])
    w = last + want - time.time()
    if w > 0:
        if log:
            log(f"  pace: between ads, waiting {w / 60:.1f} min")
        time.sleep(w)
        return w
    return 0


def card_done(brand, name):
    f = _log_file(brand)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a") as fh:
        fh.write(json.dumps({"t": time.time(), "bytes": 0, "card_done": name}) + "\n")


def sent(brand, size, name, via=None):
    f = _log_file(brand)
    f.parent.mkdir(parents=True, exist_ok=True)
    row = {"t": time.time(), "bytes": size, "file": name}
    if via:
        row["via"] = via
    with f.open("a") as fh:
        fh.write(json.dumps(row) + "\n")


# ---- Meta's usage meters ----------------------------------------------------------------------------------------
METERS = ("call_count", "total_cputime", "total_time", "acc_id_util_pct")
USAGE = {"top": 0.0, "regain_s": 0, "t": 0.0, "tier": None}     # the latest reading, this process


def read_usage(headers):
    """(top %, seconds until Meta gives access back, access tier) from one reply's headers. Missing = (0, 0, None)."""
    top, regain, tier = 0.0, 0, None
    for h in ("x-business-use-case-usage", "x-ad-account-usage", "x-app-usage"):
        try:
            stack = [json.loads((headers.get(h) if headers else None) or "null")]
        except (ValueError, TypeError):
            continue
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                for k, v in x.items():
                    if k in METERS and isinstance(v, (int, float)):
                        top = max(top, float(v))
                    elif k == "estimated_time_to_regain_access" and isinstance(v, (int, float)):
                        regain = max(regain, int(v) * 60)           # minutes
                    elif k == "reset_time_duration" and isinstance(v, (int, float)) and top >= 100:
                        regain = max(regain, int(v))                # seconds
                    elif k == "ads_api_access_tier" and isinstance(v, str):
                        tier = v
                    elif isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(x, list):
                stack += x
    return top, regain, tier


def note_usage(headers):
    """Keep the latest meter reading (every Meta reply, errors included)."""
    top, regain, tier = read_usage(headers)
    if top or regain or tier:
        USAGE.update(top=top, regain_s=regain, t=time.time(), tier=tier or USAGE["tier"])
    return top


def usage_wait(now=None):
    """Seconds to wait before the next call, from the latest meter reading (0 = go)."""
    if off() or not USAGE["t"]:
        return 0
    u = CFG.get("usage") or {}
    now = now or time.time()
    left_regain = max(0, USAGE["t"] + USAGE["regain_s"] - now)
    if left_regain:
        return left_regain + 5
    top = USAGE["top"]
    if top >= u.get("pause_at", 80):
        return max(0, USAGE["t"] + u.get("pause_min_s", 300) - now)
    lo = u.get("slow_at", 50)
    if top >= lo:
        a, b = u.get("slow_s", [4, 20])
        span = max(1.0, u.get("pause_at", 80) - lo)
        return a + (b - a) * min(1.0, (top - lo) / span)
    return 0


def before_call(log=None):
    """Slow down before Meta's limit, never run into it."""
    w = usage_wait()
    if w:
        if log and w >= 30:
            log(f"  pace: Meta's usage meter is at {USAGE['top']:.0f}%, waiting {w / 60:.1f} min before the next call")
        time.sleep(w)
    return w


def is_busy(code, body=""):
    """True when Meta is saying 'busy / slow down / try again', not 'you did it wrong'."""
    br = CFG["busy_retry"]
    if code in br["http_codes"]:
        return True
    try:
        err = json.loads(body).get("error") or {}
    except (ValueError, AttributeError):
        return False
    return bool(err.get("is_transient")) or err.get("code") in br["meta_codes"]


def busy_waits():
    br = CFG["busy_retry"]
    return [w * random.uniform(1 - br["jitter"], 1 + br["jitter"]) for w in br["waits_s"]]


def with_retry(send, describe, log=None):
    """send() -> its answer; an HTTPError Meta means as 'busy' waits and tries again. Anything else is raised as is."""
    import urllib.error
    waits = [] if off() else busy_waits()
    for i in range(len(waits) + 1):
        try:
            return send()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf8", "replace")
            note_usage(getattr(e, "headers", None))
            if i < len(waits) and is_busy(e.code, body):
                w = max(waits[i], usage_wait())          # Meta's own "regain access in N min" wins over our guess
                if log:
                    log(f"  Meta is busy ({e.code}) on {describe}, waiting {w / 60:.1f} min then trying again")
                time.sleep(w)
                continue
            raise SystemExit(f"Meta {e.code}: {body[:900]}"
                             + (" — Meta stayed busy through every wait; retry later, it resumes" if is_busy(e.code, body) else ""))
