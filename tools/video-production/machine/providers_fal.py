#!/usr/bin/env python3
"""
providers_fal.py — the fal submission path behind `run.py`.

Ported from `sequence.py` (retired) and the calls recorded in
`providers/fal.md`. Every HTTP call goes through an injectable
`transport(method, url, body, headers) -> dict`, defaulting to a plain
urllib implementation, and every download goes through an injectable
`download(url, dest) -> None`. Tests pass their own transport/download and
never touch the network. No brand, model or person name is written here —
a model slug is looked up from `providers.json` by `platform.resolve_model`
and then only ever carried opaquely (as the submit URL and the ledger's
`model` field); the body-shape mapping below dispatches on the provider-
neutral STATION name, never on a slug, so this file names no model either.

STATION -> REQUEST BODY, on fal (read `providers/fal.md` and the retired
`sequence.py`'s payload builders for where these field names came from —
the station's actual model slug for fal is `providers.json`'s own
`providers.fal.stations.<station>`):

| station | fields sent |
|---|---|
| still / cast | prompt, reference_image_urls, image_size, style, rendering_speed |
| edit (formerly restyle) | prompt, image_urls |
| motion | prompt, image_url (only when a start_image media is given), duration (STRING, not a number), resolution |
| audio | prompt, duration |

`talking` has no body mapping yet — it is a candidate station (see
`providers.json`'s `fal.talking_recipe`) and nothing here has submitted one.

`medias` role `image_references` becomes the model's reference list; role
`start_image` becomes `image_url`. This runner currently has no still
stage of its own — `run.py` turns a plan straight into "motion" items, the
same one-shot shape the Cinema line uses on Higgsfield (`prompt.py`) — so a
motion item usually carries no start_image. fal's motion station is an
image-to-video model, so a body with no `image_url` may be refused by fal
itself. That gap is real, not silently patched here; see `RUN.md`.
"""
from __future__ import annotations

import importlib.util
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUEUE = "https://queue.fal.run"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


platform = _load("platform")
preflight = _load("preflight")


# --------------------------------------------------------------- the key

def key() -> str:
    """FAL_KEY: env first, then the Keychain vault, then machine/.env — the
    same order platform.py's own vault check implies. A teammate's clone
    with none of the three gets a plain, actionable error."""
    k = os.environ.get("FAL_KEY")
    if k:
        return k
    try:
        import daemn_keys
        k = daemn_keys.key("FAL_KEY")
    except Exception:
        k = None
    if k:
        return k
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("FAL_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No FAL_KEY — set it in the environment, the Keychain "
                      "vault (daemn_keys), or machine/.env")


# ----------------------------------------------------------- the transport
#
# Every call in this module goes through one of these two seams. Nothing
# else in the file talks to urllib directly, so a test can hand run_batch()
# a fake of each and never touch the network.

def http_transport(method: str, url: str, body: dict | None, headers: dict) -> dict:
    """The real network call — the default `transport`."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def fetch(url: str, dest: Path) -> None:
    """The real download — the default `download`."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=600) as r, open(dest, "wb") as f:
        f.write(r.read())


def api(method: str, url: str, body: dict | None, k: str, transport, tries: int = 4) -> dict:
    """4 tries, backoff 20*(attempt+1)s on 408/429/5xx — ported from
    sequence.py's api()."""
    headers = {"Authorization": f"Key {k}", "Content-Type": "application/json"}
    last = None
    for attempt in range(tries):
        try:
            return transport(method, url, body, headers)
        except urllib.error.HTTPError as e:
            last = e
            transient = e.code in (408, 429, 500, 502, 503, 504)
            if transient and attempt < tries - 1:
                time.sleep(20 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {e.code} from {url}") from e
    raise RuntimeError(f"no response from {url}: {last}")


def submit(slug: str, body: dict, k: str, transport) -> dict:
    """POST {QUEUE}/{slug} — the raw submit response (status_url,
    response_url, request_id)."""
    return api("POST", f"{QUEUE}/{slug}", body, k, transport)


def wait(status_url: str, response_url: str, k: str, transport, label: str,
         poll_seconds: float = 6) -> dict:
    """Poll status_url every poll_seconds; on COMPLETED, fetch response_url.
    Ported from sequence.py's wait()."""
    while True:
        st = api("GET", status_url + "?logs=0", None, k, transport)
        status = st.get("status")
        if status == "COMPLETED":
            return api("GET", response_url, None, k, transport)
        if status in ("FAILED", "CANCELLED", "ERROR"):
            raise RuntimeError(f"{label} failed: {json.dumps(st)[:500]}")
        time.sleep(poll_seconds)


def media_urls(obj, out=None) -> list[str]:
    """Every http(s) `url` found anywhere in a response, depth-first —
    ported verbatim from sequence.py."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        u = obj.get("url")
        if isinstance(u, str) and u.startswith("http"):
            out.append(u)
        for v in obj.values():
            media_urls(v, out)
    elif isinstance(obj, list):
        for v in obj:
            media_urls(v, out)
    return out


def ext_of(url: str) -> str:
    tail = url.split("?")[0].rsplit("/", 1)[-1]
    return f".{tail.rsplit('.', 1)[-1]}" if "." in tail else ".mp4"


# --------------------------------------------------------------- the body

def body_for(station: str | None, params: dict, medias: list[dict]) -> dict:
    """A batch item's params (+ medias) -> that station's fal request body.
    Dispatches on STATION, never on a model slug — see the table up top."""
    refs = [m.get("value") for m in medias if m.get("role") == "image_references"]
    start = next((m.get("value") for m in medias if m.get("role") == "start_image"), None)
    prompt = params.get("prompt", "")
    if station in ("still", "cast"):
        return {"prompt": prompt, "reference_image_urls": refs,
                "image_size": "portrait_16_9", "style": "REALISTIC",
                "rendering_speed": "QUALITY"}
    if station == "edit":
        return {"prompt": prompt, "image_urls": refs}
    if station == "motion":
        body = {"prompt": prompt,
                "duration": str(int(params.get("duration") or 0)),
                "resolution": params.get("resolution") or "1080p"}
        if start:
            body["image_url"] = start
        return body
    if station == "audio":
        return {"prompt": prompt, "duration": params.get("duration")}
    raise SystemExit(f"providers_fal.py has no body mapping for station "
                      f"{station!r} — add one to body_for()")


def _station_of(item: dict, reg: dict) -> str | None:
    kind = item.get("kind") or platform.item_kind(item, reg)
    return reg["station_of_kind"].get(kind or "")


def print_dry_run(items: list[dict], prov: dict, reg: dict) -> None:
    """--dry-run: print exactly the body each item would submit. Nothing is
    sent, nothing is ledgered."""
    for it in items:
        slug, refusal = platform.resolve_model(it, prov, reg)
        if refusal:
            print(f"{it.get('id', '?')} · REFUSED · {refusal}")
            continue
        station = _station_of(it, reg)
        body = body_for(station, it.get("params") or {}, it.get("medias") or [])
        print(json.dumps({"id": it.get("id"), "model": slug, "station": station,
                          "body": body}, indent=1))


def run_batch(items: list[dict], prov: dict, reg: dict, run: Path, brand: str | None,
              transport=None, download=None) -> list[dict]:
    """Submit → wait → download → ledger, one item at a time.

    Returns the rows to merge into results.json:
    [{"id","job","url","seconds","status","file"?}, ...]
    """
    transport = transport or http_transport
    download = download or fetch
    k = key()
    out: list[dict] = []
    media_dir = run / "media"

    for it in items:
        iid = str(it.get("id", "?"))
        params = it.get("params") or {}
        seconds = float(params.get("duration") or it.get("seconds") or 0)
        tier = params.get("tier")
        resolution = params.get("resolution")
        slug, refusal = platform.resolve_model(it, prov, reg)

        if refusal:
            # preflight.check should have refused the whole batch before this
            # ever runs; ledgered defensively so a refusal is never silent.
            preflight.ledger(run, slug or "unknown", iid, seconds, "failed",
                              tier=tier, resolution=resolution, brand=brand,
                              shot=iid, note=refusal)
            out.append({"id": iid, "job": iid, "url": None, "seconds": seconds,
                       "status": "failed"})
            continue

        station = _station_of(it, reg)
        body = body_for(station, params, it.get("medias") or [])
        try:
            sub = submit(slug, body, k, transport)
            job = sub.get("request_id") or sub.get("status_url") or iid
            res = wait(sub["status_url"], sub["response_url"], k, transport, iid)
        except Exception as e:
            preflight.ledger(run, slug, iid, seconds, "failed", tier=tier,
                              resolution=resolution, brand=brand, shot=iid,
                              note=str(e)[:200])
            out.append({"id": iid, "job": iid, "url": None, "seconds": seconds,
                       "status": "failed"})
            continue

        urls = media_urls(res)
        if not urls:
            preflight.ledger(run, slug, job, seconds, "failed", tier=tier,
                              resolution=resolution, brand=brand, shot=iid,
                              note="no media in response")
            out.append({"id": iid, "job": job, "url": None, "seconds": seconds,
                       "status": "failed"})
            continue

        url = urls[0]
        dest = media_dir / f"{iid}{ext_of(url)}"
        download(url, dest)
        preflight.ledger(run, slug, job, seconds, "done", tier=tier,
                          resolution=resolution, brand=brand, shot=iid)
        out.append({"id": iid, "job": job, "url": url, "seconds": seconds,
                   "status": "done", "file": str(dest.relative_to(run))})

    return out
