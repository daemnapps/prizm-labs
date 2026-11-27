"""The email adapter, QB-5 (production contract): email-production's side of the production contract
(components/creative-queue/contract.py; manifest adapter.json beside this file). It WRAPS sync.py and never edits it.

    adapter.py report [--root R] [--source S] [--brand B]
        one queue observation per designed email (a run with klaviyo/card.json + design/email.json), written through
        creative-queue's own qcore.write_observation as observations/<source>.json, source = this machine's name.
        Default root runs/queue-shadow/; the live runs/queue/ is refused (exit 2) while
        components/creative-queue/live-switch.json is not "on", until QB-4 (joint queue test).
    adapter.py detail <id>
        the email's parts (JSON): [{n, kind, label, words, media: [{drive_id?, path_label}], position, ok}];
        positions from <run>/klaviyo/layout.json (LD-76 (email layout file)) only — never a browser on read: a missing
        or stale layout gives position null and "layout_stale": true
    adapter.py apply <id> <part|-> <word> [payload] --by <person>
        one change through `sync.py apply`; prints {ok, revision, message, paths, ref}; exit 0 done · 1 failed ·
        2 refused (an approval, or a word adapter.json does not list)
    adapter.py try <id> <part> <word> [payload] --by <person> [--model M] [--count N] [--from-try K]
        LD-83 (picture try first): preview results, nothing committed — for `picture` (adapter.json try_words), payload
        "<k>: <change>" as apply takes it, through try_picture.py's try_change into the run's tries/<P>/; prints
        {ok, message, tries}; the paid line goes to stderr; exit 0 made · 1 failed · 2 refused (a word not in
        try_words, an approval, a model not in the choices, no door for it yet, a missing key)

<id> is the queue id `<brand>_email_<label>` (the naming standard's shape — lab/owner/suite/queue_store.py `entry_id`,
copied as a rule, never imported) or sync.py's row id `<brand>__<label>`. <part> is the section number in
design/email.json (sync.py's `section`); `-` is the whole email.

The change words (contract.schema.json shared words, plus `fill`, listed in adapter.json) and the sync.py call each
makes:
    words    part, payload a JSON list of edits [{"path", "value", "before"?}]       -> words
    picture  part, payload "<k>: <change>" (k = the part's picture number, 0 if left out) -> picture
    redo     part -> look; whole email (-) -> send_back; payload the change, in words
    move     part, payload up | down                                               -> move
    remove   part, payload an optional reason                                      -> remove
    ok       part                                                                  -> ok
    note     whole email, payload the note                                         -> send_back
    fill     whole email                                                           -> fill
`go`, `scheduled` (and every other approval) are refused, exit 2, naming the approval path. words / picture / fill
keep the card's marks across the rebuild and stamp the build, as ask.py does (prepare.keep_card, prepare.stamp).

The stage each email reports — PROPOSED, the team confirms after:
    scheduled set -> launch · klaviyo set (a Klaviyo draft) -> launch · held reasons -> making + held ·
    no final check yet (designed, checks pending) -> making · eve_done -> final-needs-you + approved_by ·
    otherwise (ready) -> final-needs-you.
    live is UNREACHABLE: no card field records a send yet, so no email is ever reported live (said in the output).
"""
import argparse
import contextlib
import datetime as dt
import hashlib
import json
import re
import socket
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(d for d in HERE.parents if (d / "components" / "run-kit").is_dir()) / "components" / "run-kit"))
from run_kit import paths  # noqa: E402

import sync  # noqa: E402  this folder's own: KIND, fields(); it appends email-production and design/ to sys.path
import layout_file as LF  # noqa: E402  design/layout_file.py, LD-76 (email layout file)
import prepare  # noqa: E402  this folder's own: keep_card, stamp

REPO = paths.repo(HERE)
sys.path.append(str(REPO / "components" / "creative-queue"))     # appended, never ahead of this folder
import qcore  # noqa: E402  creative-queue's write_observation, check_root, shadow_root

RUNS = sync.RUNS
LEARNINGS = REPO / "runs" / "learnings"
SYNC = HERE / "sync.py"
WORDS = tuple(json.loads((HERE / "adapter.json").read_text())["words"])
TRY_WORDS = tuple(json.loads((HERE / "adapter.json").read_text()).get("try_words") or ())
APPROVALS = {
    "go": "the Klaviyo draft is an approval, not a change: the team's or the owner's Go on the email approval page "
          "(tools/email-production/email_approve.py) or ask.py's \"make the Klaviyo draft (Go)\" line, recorded "
          "on the queue as a decision (cq.py approve)",
    "scheduled": "marking an email scheduled is the team's own act after she schedules it in Klaviyo: ask.py's "
                 "\"I scheduled it in Klaviyo\" line, until the queue records it as a decision",
}
for _w in ("schedule", "send", "approve", "publish", "launch"):
    APPROVALS[_w] = "a send, schedule or approval is never a change word: it stays an approval — a queue decision " \
                    "(cq.py approve) plus a person's press on the email approval page, with a receipt"
LIVE = ("live: unreachable — no card field records a send yet, so no email is reported live (QB-5 (production "
        "contract) gap (b)); the stage mapping is PROPOSED until the team confirms")
MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".mp3", ".wav", ".psd", ".zip"}
KEEP_MARKS = {"words", "picture", "fill"}    # sync actions that rebuild the same parts (ask.py KEEP_MARKS)
SLUG = re.compile(r"[^a-z0-9._-]+")
NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class Refused(Exception):
    """An approval or a word adapter.json does not list: exit 2."""


# --------------------------------------------------------------- ids and runs

def _slug(s):
    """The naming standard's slug (queue_store.py `_slug`, copied as a rule)."""
    return SLUG.sub("-", str(s or "").lower()).strip("-")[:120]


def entry_id(brand, label):
    """`<brand>_email_<label>`: the naming standard's id for an email (queue_store.py `entry_id`, copied as a rule)."""
    return "%s_email_%s" % (_slug(brand) or "unknown", _slug(label))


def runs(brand=None):
    """Every designed email: a run with klaviyo/card.json and design/email.json, sorted."""
    out = []
    for f in sorted(Path(RUNS).glob("%s/*/klaviyo/card.json" % (brand or "*"))):
        run = f.parent.parent
        if (run / "design" / "email.json").is_file():
            out.append(run)
    return out


def resolve(item_id):
    """The run an id names (queue id or sync's <brand>__<label>), or None."""
    item_id = str(item_id or "")
    if "__" in item_id and "/" not in item_id:
        b, _, label = item_id.partition("__")
        run = Path(RUNS) / b / label
        return run if b and label and run in runs(b) else None
    return next((r for r in runs() if entry_id(r.parent.name, r.name) == item_id), None)


def _rel(p):
    p = Path(p)
    try:
        return p.resolve().relative_to(Path(REPO).resolve()).as_posix()
    except ValueError:
        return str(p)


def _read(f):
    return json.loads(Path(f).read_text())


def _held(card):
    """sync.py's held reasons: every product or final check whose result is not ok or by-hand (sync.rows, same rule)."""
    return list(dict.fromkeys(x.get("detail") for x in (card.get("product_check") or []) + (card.get("final_check") or [])
                              if x.get("result") not in ("ok", "by-hand", "note")))


def source_name():
    """This machine's name, as a queue source: lower case, '.local' dropped."""
    n = _slug(socket.gethostname())
    n = n[:-len(".local")] if n.endswith(".local") else n
    return n if NAME.match(n) else "unknown-machine"


# --------------------------------------------------------------- report

def observe(run):
    """One queue entry for a designed email (the PROPOSED stage table in this file's docstring)."""
    c, spec = _read(run / "klaviyo" / "card.json"), _read(run / "design" / "email.json")
    held = _held(c)
    e = {}
    if c.get("scheduled"):
        state, stage = "scheduled", "launch"
    elif c.get("klaviyo"):
        state, stage = "klaviyo-draft", "launch"
    elif held:
        state, stage = "held", "making"
    elif not c.get("final_check"):
        state, stage = "checks-pending", "making"
    elif c.get("eve_done"):
        state, stage = "designer-done", "final-needs-you"
        e["approved_by"] = str((c["eve_done"] or {}).get("by") or "designer").lower() if isinstance(c["eve_done"], dict) else "designer"
    else:
        state, stage = "ready", "final-needs-you"
    s0 = (c.get("subjects") or [{}])[0]
    e.update({"kind": "email", "brand": run.parent.name, "label": run.name,
              "title": s0.get("subject") or spec.get("subject") or run.name,
              "observed_stage": stage, "state": state, "held": held, "links": {"run": _rel(run)}})
    return entry_id(run.parent.name, run.name), e


def report(root=None, source=None, brand=None, now=None):
    """Write the observation file; returns the summary printed. qcore.Refused for the live queue while it is off."""
    root = qcore.check_root(root or qcore.shadow_root(REPO), repo=REPO)
    source = source or source_name()
    entries = dict(observe(r) for r in runs(brand))
    wrote = qcore.write_observation(root, source, entries, now=now)
    stages = {}
    for e in entries.values():
        stages[e["observed_stage"]] = stages.get(e["observed_stage"], 0) + 1
    return {"source": source, "root": _rel(root), "written": _rel(wrote) if wrote else None,
            "unchanged": wrote is None, "entries": len(entries), "stages": stages, "live": LIVE}


# --------------------------------------------------------------- detail

def _media(sec):
    """The pictures in a section, in sync.pictures' order (the page's picture numbers): a stored reference only."""
    out = []

    def walk(x):
        if isinstance(x, dict):
            if "alt" in x and ("photo" in x or "proof" in x or "source" in x or "todo" in x):
                ref = x.get("photo") or x.get("proof")
                m = {"path_label": ref if isinstance(ref, str) and ref else None, "alt": x.get("alt") or x.get("todo") or ""}
                if x.get("drive_id"):
                    m["drive_id"] = x["drive_id"]
                if not m["path_label"]:
                    m["state"] = "not made"
                out.append(m)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(sec)
    return out


def detail(item_id):
    """The email's parts, or None for an id that names no designed email. Reads files only: no Chrome, no process."""
    run = resolve(item_id)
    if run is None:
        return None
    c, spec = _read(run / "klaviyo" / "card.json"), _read(run / "design" / "email.json")
    d = LF.read(run)
    stale = d is None or LF.stale(run)
    H, pos = LF.positions(d) if not stale else (None, {})
    oks = set(c.get("sections_ok") or [])
    parts = []
    for i, s in enumerate(spec.get("sections") or []):
        t = s.get("s", "")
        p = pos.get(i)
        parts.append({"n": i, "kind": t, "label": sync.KIND.get(t, t.replace("_", " ").capitalize()),
                      "words": [{"path": k, "value": v} for k, v in sync.fields(s)], "media": _media(s),
                      "position": {"top": round(p[0] / H, 4), "bottom": round(p[1] / H, 4)} if p and H else None,
                      "ok": i in oks})
    s0 = (c.get("subjects") or [{}])[0]
    return {"id": entry_id(run.parent.name, run.name), "brand": run.parent.name, "label": run.name,
            "title": s0.get("subject") or spec.get("subject") or run.name, "layout_stale": stale, "parts": parts}


# --------------------------------------------------------------- apply

def _part(part):
    if part in (None, "-"):
        return None
    if not str(part).isdigit():
        raise ValueError("part must be a section number or -, got %r" % (part,))
    return int(part)


def call_for(word, part, payload, by):
    """The sync.py apply call one change word makes (without brand/label/id/at). Refused or ValueError otherwise."""
    if word in APPROVALS:
        raise Refused("%s is refused: %s" % (word, APPROVALS[word]))
    if word not in WORDS:
        raise Refused("%r is not a change word here (adapter.json words: %s)" % (word, " · ".join(WORDS)))
    i, text = _part(part), (payload or "").strip()
    k = {"by": by}
    whole = word in ("note", "fill") or (word == "redo" and i is None)
    if not whole and i is None:
        raise ValueError("%s needs a part (a section number), not -" % word)
    if word == "fill" and i is not None:
        raise ValueError("fill is for the whole email: part -")
    if i is not None and not whole:
        k["section"] = i
    if word == "words":
        try:
            edits = json.loads(text)
        except ValueError:
            raise ValueError("words needs the new words as JSON: [{\"path\": …, \"value\": …}]")
        if not isinstance(edits, list) or not edits or not all(isinstance(e, dict) and "path" in e and "value" in e
                                                               for e in edits):
            raise ValueError("words needs a list of {\"path\", \"value\"} edits")
        k.update(action="words", edits=edits)
    elif word == "picture":
        m = re.match(r"^(\d+)\s*:\s*(.*)$", text, re.S)
        n, note = (int(m.group(1)), m.group(2).strip()) if m else (0, text)
        if not note:
            raise ValueError("picture needs the change, in words")
        k.update(action="picture", picture=n, note=note)
    elif word == "redo":
        if not text:
            raise ValueError("redo needs the change, in words")
        k.update(action="look" if i is not None else "send_back", note=text)
    elif word == "move":
        if text.lower() not in ("up", "down"):
            raise ValueError("move needs up or down")
        k.update(action="move", dir=text.lower())
    elif word == "remove":
        k.update(action="remove")
        if text:
            k["note"] = text
    elif word == "ok":
        k.update(action="ok")
    elif word == "note":
        if not text:
            raise ValueError("note needs the note, in words")
        k.update(action="send_back", note=("(part %d) " % i if i is not None else "") + text)
    elif word == "fill":
        k.update(action="fill")
    return k


def run_sync(calls):
    """THE SEAM: sync.py apply as its own command (as ask.py runs it); its per-call results."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(calls, fh)
    try:
        p = subprocess.run([sys.executable, str(SYNC), "apply", fh.name], cwd=str(REPO), capture_output=True, text=True)
    finally:
        Path(fh.name).unlink()
    try:
        got = json.loads(p.stdout)
        if isinstance(got, list) and got:
            return got
    except ValueError:
        pass
    return [{"id": c.get("id"), "state": "failed", "result": (p.stderr or p.stdout).strip()[-300:]} for c in calls]


def _snapshot(run):
    """{repo-relative file: sha} for the run folder and runs/learnings, media left out (it is never in git)."""
    out = {}
    for top in (Path(run), Path(LEARNINGS)):
        if not top.is_dir():
            continue
        for f in top.rglob("*"):
            if f.is_file() and f.suffix.lower() not in MEDIA and not f.name.endswith(".tmp"):
                out[_rel(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def revision(run):
    """sha256 of klaviyo/card.json + design/email.json: changes whenever the email or its card does."""
    h = hashlib.sha256()
    for f in (run / "klaviyo" / "card.json", run / "design" / "email.json"):
        h.update(f.read_bytes() if f.is_file() else b"")
    return h.hexdigest()


def apply(item_id, part, word, payload=None, by=None):
    """One change; returns (exit code, {ok, revision, message, paths, ref})."""
    run = resolve(item_id)
    if word in APPROVALS:
        return 2, {"ok": False, "revision": revision(run) if run else None,
                   "message": "%s is refused: %s" % (word, APPROVALS[word])}
    if run is None:
        return 1, {"ok": False, "revision": None, "message": "no designed email %r (want <brand>_email_<label> or "
                   "<brand>__<label>)" % (item_id,)}
    if not by:
        return 1, {"ok": False, "revision": revision(run), "message": "who asked? --by <person>"}
    try:
        k = call_for(word, part, payload, by)
    except Refused as e:
        return 2, {"ok": False, "revision": revision(run), "message": str(e)}
    except ValueError as e:
        return 1, {"ok": False, "revision": revision(run), "message": str(e)}
    k.update({"id": uuid.uuid4().hex[:12], "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "brand": run.parent.name, "label": run.name, "email": "%s__%s" % (run.parent.name, run.name)})
    warn = ""
    try:
        drafted = (_read(run / "klaviyo" / "card.json").get("klaviyo") or {}).get("campaign_id")
    except (OSError, ValueError, AttributeError):
        drafted = None
    if drafted and k["action"] != "ok":
        warn = (" — already a Klaviyo draft (%s): this changes the email here, not the draft in Klaviyo; tell the team "
                "to make the same change there" % drafted)
    before = _snapshot(run)
    if k["action"] in KEEP_MARKS:
        r = prepare.keep_card(run, lambda: run_sync([k]))[0]
    else:
        r = run_sync([k])[0]
    ok = r.get("state") == "applied"
    if ok and k["action"] in KEEP_MARKS:
        prepare.stamp(run)
    after = _snapshot(run)
    changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
    msg = str(r.get("result") or ("done" if ok else "failed"))
    return (0 if ok else 1), {"ok": ok, "revision": revision(run), "message": msg + warn, "paths": changed,
                              "ref": _rel(run / "design" / "email.json"), "call": k["action"]}


# --------------------------------------------------------------- try (LD-83 (picture try first))

def try_(item_id, part, word, payload=None, by=None, model=None, count=1, from_try=None):
    """Preview results of one change, nothing committed; returns (exit code, {ok, message, tries})."""
    run = resolve(item_id)
    if word in APPROVALS:
        return 2, {"ok": False, "message": "%s is refused: %s" % (word, APPROVALS[word]), "tries": []}
    if run is None:
        return 1, {"ok": False, "message": "no designed email %r (want <brand>_email_<label> or <brand>__<label>)"
                   % (item_id,), "tries": []}
    if not by:
        return 1, {"ok": False, "message": "who asked? --by <person>", "tries": []}
    if word not in TRY_WORDS:
        return 2, {"ok": False, "message": "%r has no try here (adapter.json try_words: %s)"
                   % (word, " · ".join(TRY_WORDS) or "none"), "tries": []}
    try:
        k = call_for(word, part, payload, by)
    except Refused as e:
        return 2, {"ok": False, "message": str(e), "tries": []}
    except ValueError as e:
        return 1, {"ok": False, "message": str(e), "tries": []}
    import own_picture
    import try_picture
    spec = _read(run / "design" / "email.json")
    code = next(("P%d" % n for n, i, j, _ in own_picture.slots(spec) if (i, j) == (k["section"], k["picture"])), None)
    if code is None:
        return 1, {"ok": False, "message": "part %d has no picture %d" % (k["section"], k["picture"]), "tries": []}
    try:
        with contextlib.redirect_stdout(sys.stderr):        # the paid line and each try's line; stdout stays JSON
            made = try_picture.try_change(run, code, k["note"], by, model=model, count=count, from_try=from_try)
    except KeyError as e:
        return 2, {"ok": False, "message": e.args[0] if e.args else str(e), "tries": []}
    except try_picture.NoDoor as e:
        return 2, {"ok": False, "message": str(e), "tries": []}
    except (Exception, SystemExit) as e:  # noqa: BLE001 — said, never hidden (CannotRemake carries its offer)
        return 1, {"ok": False, "message": str(e)[:400], "tries": []}
    msg = "; ".join("try %d of %s: %s (%s)" % (t["n"], code, t["made"], (t["judge"] or {}).get("verdict") or "not judged")
                    for t in made) or "the try made no picture"
    return (0 if made else 1), {"ok": bool(made), "message": msg, "tries": made}


# --------------------------------------------------------------- the command

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("--root")
    r.add_argument("--source")
    r.add_argument("--brand")
    d = sub.add_parser("detail")
    d.add_argument("id")
    a = sub.add_parser("apply")
    a.add_argument("id")
    a.add_argument("part")
    a.add_argument("word")
    a.add_argument("payload", nargs="?")
    a.add_argument("--by")
    t = sub.add_parser("try")
    t.add_argument("id")
    t.add_argument("part")
    t.add_argument("word")
    t.add_argument("payload", nargs="?")
    t.add_argument("--by")
    t.add_argument("--model")
    t.add_argument("--count", type=int, default=1)
    t.add_argument("--from-try", type=int)
    x = ap.parse_args(argv)
    if x.cmd == "try":
        code, out = try_(x.id, x.part, x.word, x.payload, x.by, model=x.model, count=x.count, from_try=x.from_try)
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return code
    if x.cmd == "report":
        try:
            out = report(x.root, x.source, x.brand)
        except qcore.Refused as e:
            print(str(e), file=sys.stderr)
            return 2
        except ValueError as e:
            print("report: %s" % e, file=sys.stderr)
            return 1
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return 0
    if x.cmd == "detail":
        got = detail(x.id)
        if got is None:
            print("no designed email %r (want <brand>_email_<label> or <brand>__<label>)" % x.id, file=sys.stderr)
            return 1
        print(json.dumps(got, indent=1, ensure_ascii=False))
        return 0
    code, out = apply(x.id, x.part, x.word, x.payload, x.by)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
