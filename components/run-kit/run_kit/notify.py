"""Tell people the moment work is done (19 Oct 2026).

    from run_kit.notify import link_for, notify
    notify("timeline", "Rough cut ready: brand-a/promo-03", id_="brand-a/promo-03")

Appends one line to runs/notify/events.jsonl — a single O_APPEND write, so many machines can write at once.
It sends nothing anywhere. Outlier (lab/damon/suite) reads the file: its bell shows each event to the
person named in `who`, and for the owner alone it also messages his own phone. Never raises into the caller.

Kinds and the links they make (open Outlier on that item, on the Mac or over Tailscale):
    timeline <brand/label> · brief <queue id> · batch <batch id> · swipe <swipe key> · calls <call id>
"""
import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import quote

KINDS = ("timeline", "brief", "batch", "swipe", "calls")
BASE = os.environ.get("OUTLIER_BASE", "http://localhost:8880")


def _repo():
    try:
        from run_kit.paths import repo
        return Path(repo(__file__))
    except Exception:  # noqa: BLE001
        return Path(__file__).resolve().parents[3]


def events_file():
    return _repo() / "runs" / "notify" / "events.jsonl"


def link_for(kind, id_):
    """The shareable link that opens Outlier on `kind` with `id_` loaded."""
    if kind not in KINDS:
        raise ValueError("kind must be one of %s" % ", ".join(KINDS))
    return "%s/%s/%s" % (BASE.rstrip("/"), kind, quote(str(id_), safe=""))


def notify(kind, title, link=None, who="damon", id_=None):
    ev = {"id": uuid.uuid4().hex[:12], "ts": time.time(), "when": time.strftime("%Y-%m-%d %H:%M"),
          "kind": kind, "title": str(title)[:300], "who": (who or "damon").lower(), "link": link or ""}
    try:
        if not ev["link"] and id_ is not None:
            ev["link"] = link_for(kind, id_)
        f = events_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(f), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, (json.dumps(ev) + "\n").encode())
        finally:
            os.close(fd)
    except Exception as e:  # noqa: BLE001
        print("notify: could not write the event: %s" % e, file=sys.stderr)
    return ev


def safe_notify(kind, title, id_, who="damon", label=""):
    """For machines: skip test runs (v2test-*), never fail the run."""
    if str(label or id_).split("/")[-1].startswith("v2test-"):
        return None
    try:
        return notify(kind, title, who=who, id_=id_)
    except Exception:  # noqa: BLE001
        return None
