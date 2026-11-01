"""pace — the uploader moves like a person, not a script (the owner, 21 Oct 2026).

Three things, all set in pace.json:

* **Breathing room.** A short random pause between the pieces of one video, a longer one between videos, and a
  long one between ads, so a batch never arrives as one burst.
* **An hourly budget.** No more than `per_hour.bytes` sent and `per_hour.videos` videos in any rolling hour; past it
  the uploader waits until the hour frees up. Counted in runs/meta-upload/<brand>/pace.jsonl, so the budget holds
  across ads, retries and a restarted approve page.
* **Busy means wait, not quit.** A 5xx from Meta, or one of Meta's own "slow down / try again" error codes, waits
  (45 s, 2 min, 5 min, 10 min, each with a little jitter) and tries the same call again. Only after the last wait
  does it stop, and the upload resumes from upload-state.json on retry.

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


def sent(brand, size, name):
    f = _log_file(brand)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a") as fh:
        fh.write(json.dumps({"t": time.time(), "bytes": size, "file": name}) + "\n")


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
            if i < len(waits) and is_busy(e.code, body):
                if log:
                    log(f"  Meta is busy ({e.code}) on {describe}, waiting {waits[i] / 60:.1f} min then trying again")
                time.sleep(waits[i])
                continue
            raise SystemExit(f"Meta {e.code}: {body[:900]}"
                             + (" — Meta stayed busy through every wait; retry later, it resumes" if is_busy(e.code, body) else ""))
