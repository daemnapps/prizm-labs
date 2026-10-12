"""The shared back half of the free internal-source modes — `surveys`,
`reviews`, `interviews` (built 2026-09-29 on the owner's ruling: automate the
sources that cost nothing; Apify stays on request).

Every mode pulls its own rows, then hands them here:

    rows -> de-dupe against the avatar bank by `ref` -> intake read + the
    language layer's labeller (annotate.read_and_sort, the same pipeline
    ownvoice and comments file through) -> the mode's extras laid on
    (origin internal, source.item, a rating in signal, a forced lane) ->
    filed into the avatar's lane files -> a run record under
    runs/research/<brand>/<mode>-<run>/ (filed/dropped/held.json, report.md,
    run.json, page.html).

What a brand pulls is config in its own `operations/language-pulls.json`
(`language_avatar`, `surveys`, `reviews`, `interviews`) — never here. A key is
read by NAME (environment first, then the Keychain via daemn_keys). Never
raises on a missing source: the mode says what is missing and moves on.
"""
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from . import engine
from . import annotate as A


def say(m):
    print(m, flush=True)


# ---------------------------------------------------------------- config

def cfg(mode):
    """research.json › <mode>, with the ownvoice defaults under it."""
    c = dict(engine._config().get("ownvoice", {}))
    c.update(engine._config().get(mode, {}))
    c.setdefault("model", "claude-sonnet-5")
    c.setdefault("batch", 30)
    return c


def brand_json(brand):
    """brand.json (for the label) with operations/language-pulls.json laid over
    it — what this brand pulls. The pulls live in their own file because the
    metrics checker refuses brand.json keys it does not know."""
    ops = engine.WORKSPACE / "brands" / brand / "operations"
    out = {}
    for name in ("brand.json", "language-pulls.json"):
        try:
            out.update(json.loads((ops / name).read_text()))
        except Exception:
            pass
    return out


def avatar_for(brand, bj, named=None):
    """--avatar, else brand.json › language_avatar, else the only avatar with a bank."""
    if named:
        return named
    if bj.get("language_avatar"):
        return bj["language_avatar"]
    d = engine.WORKSPACE / "brands" / brand / "core-avatars"
    avs = sorted(p.name for p in d.iterdir() if (p / "language").is_dir()) if d.is_dir() else []
    return avs[0] if len(avs) == 1 else None


def key(name):
    """A key by NAME: the environment, then the Keychain. Never printed."""
    if not name:
        return None
    if os.environ.get(name):
        return os.environ[name]
    try:
        p = str(Path.home() / ".daemn")
        if p not in sys.path:
            sys.path.append(p)
        import daemn_keys  # noqa: E402
        return daemn_keys.key(name)
    except Exception:
        return None


def runs_root(brand):
    return engine._deep_runs_root() / brand


def load_state(brand, mode):
    try:
        return json.loads((runs_root(brand) / f"{mode}-state.json").read_text())
    except Exception:
        return {}


def save_state(brand, mode, state):
    f = runs_root(brand) / f"{mode}-state.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")


def rid(*parts):
    """A stable short id from values that are never stored (a timestamp plus an
    email, say): the same response always gets the same id."""
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", (t or "").lower())).strip()


def bank_texts(ldir, source_id):
    """Normalised words already in the avatar bank from one source id — the
    overlap guard for sources first imported by hand, whose rows carry no ref
    to match on."""
    out = set()
    for f in ldir.parent.rglob("*.json"):
        if "/used/" in str(f):
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for e in d.get("entries", []) if isinstance(d, dict) else []:
            if (e.get("source") or {}).get("id") == source_id:
                out.add(norm(e.get("text")))
    return out


# ---------------------------------------------------------------- filing

EXTRA_SOURCE = ("item",)
CHURNED = {"cancel-subscription": "churned-subscriber"}


def lay_extras(lane, e, row):
    """What these modes add on top of build_entry: origin internal (our own
    relationship with the speaker — ruled 2026-09-28), the platform's own id,
    a rating, and a lane the source itself decides (a refund survey's answers
    are churned, whatever the intake read called the exit)."""
    e["origin"] = "internal"
    for k in EXTRA_SOURCE:
        if row.get(k) is not None:
            e["source"][k] = row[k]
    if row.get("rating") is not None:
        e["signal"] = dict(e.get("signal") or {}, rating=row["rating"])
    force = row.get("force_lane")
    if force == "churned" and lane in ("customer", "churned-subscriber", "churned-non-subscriber"):
        if lane == "customer":
            lane = "churned-non-subscriber"
            e["funnel"] = e["speaker"] = "churned"
            e["lane_by"] = "relationship"
            e.pop("attribution", None)
    # The feedback forms (2026-09-29): the flow that sent the form KNOWS the
    # relationship — a list or checkout stage is a lead, a cancelled
    # subscription is a churned subscriber — so the stage sets the lane.
    elif force == "churned-subscriber" and lane != "churned-subscriber":
        lane = "churned-subscriber"
        e["funnel"] = e["speaker"] = "churned"
        e["lane_by"] = "relationship"
        e.pop("attribution", None)
    elif force in ("lead", "prospect") and lane != force:
        lane = force
        e["funnel"] = e["speaker"] = force
        e["lane_by"] = "relationship"
        e.pop("attribution", None)
    elif force in ("lead", "prospect"):
        e["lane_by"] = "relationship"
    if row.get("feedback"):
        e["feedback"] = row["feedback"]
    return lane, e


def file_rows(brand, avatar, label, rows, source, c, run_label, dry_run=False, labeller=None, claude=None):
    """De-dupe, read, lay extras, file. Returns (fresh, filed, dropped, held);
    filed is None on a dry run or when nothing is new."""
    ldir = A.lang_dir(brand, avatar)
    have = A.bank_refs(ldir)
    seen, fresh = set(), []
    for r in rows:
        k = (r.get("source_id"), r.get("post"), norm(r["text"]))
        if r["ref"] in have or len(r["text"].strip()) < 2 or k in seen:
            continue
        seen.add(k)
        fresh.append(r)
    say(f"  {len(rows)} pulled · {len(rows) - len(fresh)} already in the bank · {len(fresh)} new")
    if dry_run or not fresh:
        return fresh, None, [], []
    lane_entries, dropped, held = A.read_and_sort(fresh, brand, avatar, label, source, c, run_label,
                                                  labeller=labeller, claude=claude)
    by_ref = {r["ref"]: r for r in fresh}
    by_lane = {}
    for lane, e in lane_entries:
        lane, e = lay_extras(lane, e, by_ref.get(e["source"]["ref"], {}))
        by_lane.setdefault(lane, []).append(e)
    filed = A.file_lanes(ldir, by_lane)
    return fresh, filed, dropped, held


INTRO = re.compile(r"<h1>New words from our own audience</h1>\s*<p class=\"m\">.*?</p>", re.S)


def write_run(brand, mode, label, run_label, since, filed, dropped, held, notes, extra=None, intro=None):
    """The run record, the same shape ownvoice writes."""
    from . import ownvoice as OV
    import html as _h
    rep = A.report(filed, dropped, held)
    out = runs_root(brand) / f"{mode}-{run_label}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "filed.json").write_text(json.dumps(filed, indent=1, ensure_ascii=False))
    (out / "dropped.json").write_text(json.dumps(dropped, indent=1, ensure_ascii=False))
    (out / "held.json").write_text(json.dumps(held, indent=1, ensure_ascii=False))
    (out / "report.md").write_text(A.report_md(rep, f"{label} {mode} · {run_label} · since {since}"))
    (out / "run.json").write_text(json.dumps({"brand": brand, "mode": mode, "since": since, "run": run_label,
                                              **(extra or {}), "report": rep, "notes": notes}, indent=1))
    page = OV.render_page(label, run_label, since, filed, dropped, rep, A.PROMPT.read_text(), notes)
    if intro:
        page = INTRO.sub(f"<h1>New words from our own customers</h1>\n<p class=\"m\">{_h.escape(intro)}</p>", page, 1)
    page = page.replace("voice bank intake · ", f"voice bank intake · {mode} · ", 1)
    (out / "page.html").write_text(page)
    say(f"  filed {len(filed)} · dropped {len(dropped)} · held {len(held)} · thin levels: {', '.join(rep['thin_levels']) or 'none'}")
    say(f"  page: {out / 'page.html'}")
    return out, rep


def now_labels():
    now = dt.datetime.now(dt.timezone.utc)
    return now, now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d-%H%M")
