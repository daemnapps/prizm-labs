#!/usr/bin/env python3
"""revision: the owner's feedback on one piece in; only the shifts he asked for out. The chain is not run again.

    revise.py list    --brand B                          the notes waiting for a revision
    revise.py run     --brand B --note ID [--dry-run]    revise one note (a proposal: the live files are untouched)
    revise.py run     --brand B --all-new [--max N]      every note still marked new (the nightly run; exit 3 if none)
    revise.py use     --brand B --note ID                put the revised files in place (the old ones kept), run checks
    revise.py show    --brand B --note ID                the note's revision record
    revise.py ask     --brand B --input "<id>|use <id>" [--out result.md]    what the Studio's "revise" job runs

Where feedback lands: runs/studio-feedback/<brand>/feedback.jsonl (the Studio's feedback box on every piece). A note
names its piece (`item`): p:<brief key> a production, w:<label> a workflow piece, t:<label> a teardown, e:<label> an
email. It may carry typed words, a Tella recording (transcript.md, frames/), or both.

Two model passes, both on the "first drafts" tier of components/job-meter/model-map.json (never the owner's top tier):
  1. route: split his feedback into asks (exact words or a general direction) and name the file that owns each one
     (owners.json): the cheapest stage that holds that thing. Reads only the files' outlines.
  2. edit:  find-and-replace edits on only those files. Exact words go in as written.
Then code: each edit must match its file once; the diff, the before and after, the checks; nothing is overwritten.

Every revision is a record: runs/revision/<brand>/<revision id>/ with record.json, why.md (what changed and why, tied
to his words), diff.patch, before/ and after/ (only the changed files), and the prompts and replies of both passes.
`run` never touches the piece's live files; `use` puts the new versions in place and keeps each old one beside it as
<name>.before-rev-<id>.md (the chain's own naming for an earlier version). Nothing here spends beyond the two model
passes: a change that needs new footage, clips or a voice is listed and stops at the quote, as the chain does.

On `use` the chain learns from it: each kept edit and each ask's lesson go into run-kit's learnings loop (candidates;
in force at once when he stated a standing rule, else once the same change recurs in a second run), and every later
run is handed the rules in force at its station. A proposal he never uses teaches nothing.

Python 3.9, standard library only.
"""
import argparse
import datetime as dt
import difflib
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get("PRIZM_WS") or HERE.parents[1])
COMPONENTS = HERE.parent
SAFE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*\Z")
TOP_TIER = {"claude-opus-5-5", "claude-fable-5-2"}       # the owner's plan pays only for these: never here
TIER = "first drafts"                                    # model-map.json row this job runs on
MAX_FILE_CHARS = 160_000
MAX_TELLA_CHARS = 60_000
MAX_STILLS = 8


# ------------------------------------------------------------------ small helpers
def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def rel(p):
    p = Path(p)
    try:
        return str(p.resolve().relative_to(WS.resolve()))
    except ValueError:
        return str(p)


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def write_json(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, p)


def owners():
    return read_json(HERE / "owners.json", {})


def model():
    """The model of the "first drafts" row in the job meter's model map. Never the top tier."""
    mm = read_json(COMPONENTS / "job-meter" / "model-map.json", {}) or {}
    m = next((j.get("model") for j in mm.get("jobs", []) if str(j.get("kind", "")).startswith(TIER)), None)
    m = os.environ.get("REVISION_MODEL") or m or "claude-sonnet-5-5"
    if m in TOP_TIER:
        raise SystemExit("the revision never runs on the owner's top tier (%s); fix the model map's %r row" % (m, TIER))
    return m


def effort():
    try:
        sys.path.append(str(COMPONENTS / "run-kit"))
        from run_kit.claude_flags import EFFORT
        return EFFORT
    except Exception:  # noqa: BLE001
        return "medium"


# ------------------------------------------------------------------ the notes
def fb_file(brand):
    return WS / "runs" / "studio-feedback" / brand / "feedback.jsonl"


def notes(brand):
    f = fb_file(brand)
    out = []
    if f.is_file():
        for line in f.read_text(errors="replace").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def note(brand, nid):
    n = next((x for x in notes(brand) if x.get("id") == nid), None)
    if not n:
        raise SystemExit("no note %s for %s" % (nid, brand))
    return n


def mark(brand, nid, **fields):
    """Update one note in place. Locked, and re-read under the lock, so a note the Studio adds meanwhile is kept."""
    f = fb_file(brand)
    with open(f, "r+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        lines = fh.read().splitlines()
        out = []
        for line in lines:
            try:
                r = json.loads(line)
            except ValueError:
                out.append(line)
                continue
            if r.get("id") == nid:
                r.update({k: v for k, v in fields.items() if v is not None})
                for k in [k for k, v in fields.items() if v is None]:
                    r.pop(k, None)
            out.append(json.dumps(r, ensure_ascii=False))
        fh.seek(0)
        fh.write("\n".join(out) + "\n")
        fh.truncate()
        fcntl.flock(fh, fcntl.LOCK_UN)


# ------------------------------------------------------------------ the piece
def _register_entry(key):
    reg = read_json(COMPONENTS / "image-teardown" / "briefs.json", {}) or {}
    rows = reg.get("briefs") or {}
    rows = rows.values() if isinstance(rows, dict) else rows
    for r in rows:
        if isinstance(r, dict) and key in (r.get("key"), r.get("brief_key"), r.get("id"), r.get("brief")):
            return r
    return None


def _studio_brief(key):
    for bp in sorted((WS / "runs" / "video-studio" / "briefs").glob("*/brief.json")):
        b = read_json(bp, {}) or {}
        if key in (b.get("brief_key"), b.get("brief")):
            return b
    return None


def _run_from(values):
    """A teardown/writing run folder named by a record's fields."""
    for k in ("writing_run", "run", "teardown_run"):
        v = values.get(k)
        if v and (WS / v / "run.json").is_file():
            return WS / v
    td = values.get("teardown") or values.get("label")
    if td and SAFE.match(str(td)) and (WS / "runs/video-teardown/_work" / td / "run.json").is_file():
        return WS / "runs/video-teardown/_work" / td
    b = values.get("brief")
    if b and (WS / b).is_file():
        d = (WS / b).parent
        return d.parent if d.name == "stages" else d
    return None


def locate(brand, item):
    """The piece's run folder and kind: {"type": "video"|"email", "run": Path, "label": str}."""
    kind, _, ref = str(item).partition(":")
    if not ref:
        raise ValueError("a note must name its piece (p:, w:, t: or e:)")
    if kind == "e":
        d = WS / "runs" / "email-production" / brand / ref
        if SAFE.match(ref) and (d / "run.json").is_file():
            return {"type": "email", "run": d, "label": ref}
        raise ValueError("no email run %s" % ref)
    if kind in ("t", "w"):
        if kind == "w" and SAFE.match(ref):
            st = read_json(WS / "runs/video-production" / brand / ("workflow-" + ref) / "workflow-state.json", {}) or {}
            d = _run_from(st.get("values") or {})
            if d:
                return {"type": "video", "run": d, "label": ref}
        d = WS / "runs/video-teardown/_work" / ref
        if SAFE.match(ref) and (d / "run.json").is_file():
            return {"type": "video", "run": d, "label": ref}
        raise ValueError("no teardown or writing run %s" % ref)
    if kind == "p":
        for rec in (_register_entry(ref), _studio_brief(ref)):
            d = _run_from(rec) if rec else None
            if d:
                return {"type": "video", "run": d, "label": ref}
        num = re.search(r"brief-(\d{3,5})", ref)
        if num:
            for rj in sorted((WS / "runs/video-teardown/_work").glob("*/run.json")):
                r = read_json(rj, {}) or {}
                if num.group(1) in json.dumps({k: r.get(k) for k in ("brief", "brief_key", "names", "label")}):
                    return {"type": "video", "run": rj.parent, "label": ref}
        raise ValueError("no writing run found for production %s" % ref)
    raise ValueError("unknown piece kind %r" % kind)


def piece_files(where):
    """The owner rows of this piece's type, each with the first of its files that exists here."""
    out = []
    for row in owners().get(where["type"], []):
        f = next((x for x in row["files"] if (where["run"] / x).is_file()), None)
        if f:
            out.append(dict(row, file=f))
    return out


def outline(text, limit=40):
    """Headings and table headers only: what a file holds, for the routing pass."""
    keep = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("#")]
    return keep[:limit]


# ------------------------------------------------------------------ the owner's words
def tella_pack(n):
    t = n.get("tella") or {}
    folder = Path(t.get("folder") or "")
    if not t or not folder.is_dir():
        return "", [], None
    tr = folder / "transcript.md"
    words = tr.read_text(errors="replace")[:MAX_TELLA_CHARS] if tr.is_file() else ""
    stills = sorted((folder / "frames").glob("t*.jpg")) if (folder / "frames").is_dir() else []
    if len(stills) > 40:                                   # one still every few seconds: keep an even spread
        step = len(stills) / 40.0
        stills = [stills[int(i * step)] for i in range(40)]
    txt = ("## His recording (Tella: %s)\n\nEvery word he said, with its time:\n\n%s\n" % (t.get("title", ""), words)
           if words else "")
    if stills:
        txt += ("\nStills of his screen, one every few seconds (file name = the second, t0045 = 0:45). Read at most "
                "%d, only at the moments he points at something:\n%s\n" % (MAX_STILLS, "\n".join(str(s) for s in stills)))
    return txt, stills, folder


def note_text(n):
    return n.get("text").strip() if n.get("text") else "(no typed words: see his recording)"


# ------------------------------------------------------------------ the model
def call_model(prompt, mdl, read_dir=None, runner=None):
    """One `claude -p` call, lean (from a temp folder, no tools unless his stills must be read). Returns
    (text, meter). `runner` is the tests' stand-in."""
    if runner:
        return runner(prompt)
    argv = ["claude", "-p", "--model", mdl, "--output-format", "json", "--effort", effort(),
            "--strict-mcp-config", "--setting-sources", ""]
    argv += ["--tools", "Read", "--allowedTools", "Read", "--add-dir", str(read_dir)] if read_dir else ["--tools", ""]
    tmp = tempfile.mkdtemp(prefix="revision-")
    try:
        r = subprocess.run(argv, input=prompt, capture_output=True, text=True, cwd=tmp, timeout=1800)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        ev = json.loads(r.stdout)
    except ValueError:
        raise RuntimeError("the model call did not answer: " + (r.stderr or r.stdout).strip()[-300:])
    if ev.get("is_error"):
        raise RuntimeError("the model call failed: " + str(ev.get("result"))[-300:])
    u = ev.get("usage") or {}
    meter = {"model": mdl, "cost_usd": ev.get("total_cost_usd"),
             "tokens_in": (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
             + (u.get("cache_read_input_tokens") or 0), "tokens_out": u.get("output_tokens") or 0,
             "seconds": round((ev.get("duration_ms") or 0) / 1000)}
    return ev.get("result") or "", meter


def first_json(text):
    """The first complete JSON object in a reply."""
    i = text.find("{")
    if i < 0:
        raise ValueError("no JSON in the reply")
    obj, _ = json.JSONDecoder().raw_decode(text[i:])
    return obj


# ------------------------------------------------------------------ edits
def apply_edits(texts, edits):
    """Apply find/replace edits to copies. Each `find` must be in its file exactly once (after earlier edits).
    Returns (new texts, kept edits, refused edits)."""
    new, kept, refused = dict(texts), [], []
    for e in edits:
        f, find, rep = e.get("file"), e.get("find") or "", e.get("replace")
        if f not in new:
            refused.append(dict(e, refused="not one of this piece's files"))
            continue
        if not find or rep is None or find == rep:
            refused.append(dict(e, refused="empty or no change"))
            continue
        c = new[f].count(find)
        if c != 1:
            refused.append(dict(e, refused="the text to change was found %d times, not once" % c))
            continue
        at = new[f].index(find)
        if in_data_block(new[f], at, at + len(find)) and find.count("\n") != rep.count("\n"):
            refused.append(dict(e, refused="a data block the machines read keeps its shape: values only"))
            continue
        new[f] = new[f].replace(find, rep, 1)
        kept.append(e)
    return new, kept, refused


def in_data_block(text, start, end):
    """True when [start, end) touches a fenced block (```), which the machines after this step read."""
    for m in re.finditer(r"^```[^\n]*\n.*?^```", text, re.M | re.S):
        if start < m.end() and end > m.start():
            return True
    return False


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("…", " ").replace("—", " ").lower()
    return " ".join(re.sub(r"[^a-z0-9' ]", " ", s).split())


def words_check(asks, after_texts):
    """Every exact word he gave is in the revised piece (case and punctuation aside)."""
    body = norm(" ".join(after_texts.values()))
    out = []
    for a in asks:
        for w in a.get("exact_words") or []:
            if w and w.strip():
                out.append({"words": w, "in": norm(w) in body})
    return out


def script_check(path):
    """video-writing's free script check on one file: (fails, rows) or None when the file holds no timed script."""
    sc = COMPONENTS / "video-writing" / "machine" / "script_check.py"
    if not sc.is_file():
        return None
    try:
        r = subprocess.run([sys.executable, str(sc), str(path), "--json"], capture_output=True, text=True, timeout=120)
        rep = first_json(r.stdout)
    except (ValueError, subprocess.SubprocessError, OSError):
        return None
    checks = rep.get("checks") or rep.get("results") or []
    rows = rep.get("rows") or rep.get("rows_checked") or 0
    if isinstance(rows, list):
        rows = len(rows)
    if not rows:
        return None
    return {"rows": rows, "fails": sum(1 for c in checks if str(c.get("level", "")).upper() == "FAIL")}


def owner_words(run_dir, after_texts):
    """video-writing's owner-words check (writing_v2.owner_words_check) on the revised brief, in a copy of the run's
    record: every line of the owner's locked script must still be in the brief. None = no locked script."""
    st = read_json(run_dir / "run.json", {}) or {}
    if not st.get("owner_script"):
        return None
    tmp = Path(tempfile.mkdtemp(prefix="revision-owner-"))
    try:
        (tmp / "stages").mkdir()
        shutil.copy2(run_dir / "run.json", tmp / "run.json")
        own = (st["owner_script"] or {}).get("file") or "owner-script.md"
        brief = ((st.get("stages") or {}).get("stage5") or {}).get("out", "stages/5-brief.md")
        for f in (own, brief):
            src = after_texts.get(f)
            if src is None and (run_dir / f).is_file():
                src = (run_dir / f).read_text(errors="replace")
            if src is not None:
                (tmp / f).parent.mkdir(parents=True, exist_ok=True)
                (tmp / f).write_text(src)
        sys.path.insert(0, str(COMPONENTS / "video-writing" / "machine"))
        import writing_v2  # noqa: E402  (the chain's own check, called, never edited)
        missed = writing_v2.owner_words_check(tmp, st)
        return None if missed is None else {"passed": not missed, "missing": missed}
    except Exception as e:  # noqa: BLE001
        return {"passed": None, "not_run": "%s: %s" % (type(e).__name__, str(e)[:160])}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def checks(where, files, before, after, asks):
    out = {"exact_words": words_check(asks, after)}
    if where["type"] == "video":
        sc = []
        tmp = Path(tempfile.mkdtemp(prefix="revision-check-"))
        try:
            for f in files:
                b, a = tmp / ("before-" + Path(f).name), tmp / ("after-" + Path(f).name)
                b.write_text(before[f])
                a.write_text(after[f])
                rb, ra = script_check(b), script_check(a)
                if rb or ra:
                    sc.append({"file": f, "before": rb, "after": ra})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        out["script_check"] = sc
        out["owner_words"] = owner_words(where["run"], after)
    held = [w["words"] for w in out["exact_words"] if not w["in"]]
    ow = out.get("owner_words") or {}
    worse = [s["file"] for s in out.get("script_check", []) if s["before"] and s["after"]
             and s["after"]["fails"] > s["before"]["fails"]]
    out["passed"] = not held and ow.get("passed") is not False
    out["why"] = "; ".join(filter(None, [
        held and "his exact words are not all in: " + " | ".join(held),
        ow.get("passed") is False and "the owner's locked lines are no longer all in the brief"])) or None
    # the script check is report-only (its own rule): more fails are said, never a hold; his words win
    out["note"] = ("the script check finds more fails than before in " + ", ".join(worse)) if worse else None
    return out


def diff_of(files, before, after):
    out = []
    for f in files:
        out += difflib.unified_diff(before[f].splitlines(True), after[f].splitlines(True), "a/" + f, "b/" + f, n=2)
    return "".join(out)


# ------------------------------------------------------------------ one revision
def revise(brand, nid, dry=False, runner=None, say=print):
    n = note(brand, nid)
    where = locate(brand, n.get("item", ""))
    rows = piece_files(where)
    if not rows:
        raise ValueError("this piece has no stage files to revise yet")
    mdl = model()
    rid = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + nid
    out = WS / "runs" / "revision" / brand / rid
    piece = "%s (%s) · run %s" % (n.get("title") or n.get("item"), n.get("item"), rel(where["run"]))
    tella_txt, stills, tdir = tella_pack(n)
    texts = {r["file"]: (where["run"] / r["file"]).read_text(errors="replace") for r in rows}
    if not dry:
        mark(brand, nid, state="revising", revising_since=now())
    meters = []
    try:
        say("route: reading his %s" % ("words and recording" if tella_txt and n.get("text") else
                                       "recording" if tella_txt else "words"))
        files_list = "\n".join("- **%s** owns %s: `%s` (%d characters)\n  outline: %s" % (
            r["owner"], r["what"], r["file"], len(texts[r["file"]]), " · ".join(outline(texts[r["file"]], 25)) or "—")
            for r in rows)
        p1 = (HERE / "prompts" / "route.md").read_text().replace("{{PIECE}}", piece).replace(
            "{{NOTE}}", note_text(n)).replace("{{TELLA}}", tella_txt).replace("{{FILES}}", files_list)
        t1, m1 = call_model(p1, mdl, tdir if stills else None, runner)
        meters.append(dict(m1, step="route"))
        route = first_json(t1)
        asks = route.get("asks") or []
        chosen = []
        for a in asks:
            for f in a.get("files") or []:
                if f in texts and f not in chosen:
                    chosen.append(f)
        edits, kept, refused, t2, p2, summary, not_done = [], [], [], "", "", "", []
        if chosen:
            say("edit: %d ask(s) on %s" % (len(asks), ", ".join(chosen)))
            ftxt = "\n\n".join("### FILE: %s\n\n```\n%s\n```" % (f, texts[f][:MAX_FILE_CHARS]) for f in chosen)
            p2 = (HERE / "prompts" / "edit.md").read_text().replace("{{PIECE}}", piece).replace(
                "{{NOTE}}", note_text(n)).replace("{{TELLA}}", tella_txt).replace(
                "{{ASKS}}", json.dumps(asks, indent=1, ensure_ascii=False)).replace("{{FILES}}", ftxt)
            t2, m2 = call_model(p2, mdl, tdir if stills else None, runner)
            meters.append(dict(m2, step="edit"))
            ans = first_json(t2)
            edits, summary, not_done = ans.get("edits") or [], ans.get("summary") or "", ans.get("not_done") or []
        after, kept, refused = apply_edits({f: texts[f] for f in chosen}, edits)
        changed = [f for f in chosen if after[f] != texts[f]]
        before = {f: texts[f] for f in changed}
        after = {f: after[f] for f in changed}
        ck = checks(where, changed, before, after, asks) if changed else {"passed": None, "why": "nothing changed"}
        rec = {"id": rid, "at": now(), "brand": brand, "note": nid, "item": n.get("item"), "title": n.get("title"),
               "piece_type": where["type"], "run": rel(where["run"]), "model": mdl, "dry_run": dry,
               "his_words": n.get("text") or "", "tella": {k: v for k, v in (n.get("tella") or {}).items() if k != "folder"} or None,
               "read": route.get("read"), "asks": asks, "needs_paid": route.get("needs_paid") or [],
               "not_here": route.get("not_here") or [], "not_done": not_done, "summary": summary,
               "edits": kept, "refused": refused, "files": changed, "checks": ck, "meter": meters,
               "cost_usd": round(sum(m.get("cost_usd") or 0 for m in meters), 4),
               "state": "proposed" if changed else "nothing to change", "in_use": False}
        out.mkdir(parents=True, exist_ok=True)
        for f in changed:
            for side, src in (("before", before), ("after", after)):
                p = out / side / f
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(src[f])
        (out / "diff.patch").write_text(diff_of(changed, before, after))
        (out / "route.prompt.md").write_text(p1)
        (out / "route.reply.md").write_text(t1)
        if p2:
            (out / "edit.prompt.md").write_text(p2)
            (out / "edit.reply.md").write_text(t2)
        (out / "why.md").write_text(why_md(rec))
        write_json(out / "record.json", rec)
        if not dry:
            mark(brand, nid, state="revised" if changed else "nothing to change", revision=rel(out / "record.json"),
                 revision_view=view(rec), revising_since=None)
        return rec
    except Exception:
        if not dry:
            mark(brand, nid, state="new", revising_since=None)
        raise


def view(rec):
    """What the Studio shows under the note: compact, his words beside each change."""
    return {"id": rec["id"], "state": rec["state"], "in_use": rec.get("in_use", False), "read": rec.get("read"),
            "summary": rec.get("summary"), "passed": rec["checks"].get("passed"), "why_held": rec["checks"].get("why"),
            "check_note": rec["checks"].get("note"),
            "changes": [{"file": e["file"], "why": e.get("why"), "quote": e.get("quote"),
                         "before": e["find"][:1200], "after": e["replace"][:1200]} for e in rec["edits"]][:12],
            "needs_paid": [x.get("what") or x.get("quote") for x in rec.get("needs_paid") or []][:5],
            "not_done": [(x.get("quote") or "") + " — " + (x.get("why") or "") for x in
                         (rec.get("not_here") or []) + (rec.get("not_done") or [])][:5],
            "record": "runs/revision/%s/%s" % (rec["brand"], rec["id"]), "cost_usd": rec.get("cost_usd"),
            "lessons": [{"rule": a["lesson"], "said": bool(a.get("rule_said"))} for a in rec.get("asks") or []
                        if (a.get("lesson") or "").strip()][:6],
            "learned": {"filed": len(rec.get("learned") or []),
                        "in_force": [x["rule"] for x in rec.get("learned") or [] if x["promoted"]][:6]}
            if rec.get("in_use") else None}


def why_md(rec):
    L = ["# Revision %s" % rec["id"], "",
         "**Piece:** %s · `%s`  " % (rec.get("title") or rec["item"], rec["run"]),
         "**His words:** %s  " % ((rec["his_words"] or "—").replace("\n", " ")[:600]),
         "**Recording:** %s  " % ((rec.get("tella") or {}).get("title") or "—"),
         "**Read:** %s  " % (rec.get("read") or "—"),
         "**State:** %s · checks %s · %s · $%.2f" % (rec["state"], {True: "pass", False: "held", None: "—"}[
             rec["checks"].get("passed")], rec["model"], rec.get("cost_usd") or 0), ""]
    if rec["checks"].get("why"):
        L += ["> Held: " + rec["checks"]["why"], ""]
    if rec["checks"].get("note"):
        L += ["> Script check: " + rec["checks"]["note"], ""]
    L += ["## What changed and why", ""]
    for i, e in enumerate(rec["edits"], 1):
        L += ["### %d. `%s`" % (i, e["file"]), "", "- **Why:** %s" % e.get("why", ""),
              "- **His words:** “%s”" % e.get("quote", ""), "", "Before:", "", "```", e["find"].strip(), "```",
              "", "After:", "", "```", e["replace"].strip(), "```", ""]
    lessons = [a for a in rec.get("asks") or [] if (a.get("lesson") or "").strip()]
    if lessons:
        L += ["## What the chain learns from it (filed on Use this)", ""] + [
            "- %s %s%s" % ("NEVER:" if a.get("lesson_kind") == "never" else "DO:", a["lesson"],
                           " (said as a rule: in force at once)" if a.get("rule_said") else " (in force once seen twice)")
            for a in lessons] + [""]
    for title, rows in (("Needs money (stops at the quote)", rec.get("needs_paid")),
                        ("Not changed here", (rec.get("not_here") or []) + (rec.get("not_done") or [])),
                        ("Edits refused by the check", rec.get("refused"))):
        if rows:
            L += ["## " + title, ""] + ["- “%s”: %s" % (r.get("quote", ""), r.get("what") or r.get("why")
                                                                   or r.get("refused", "")) for r in rows] + [""]
    return "\n".join(L)


# ------------------------------------------------------------------ learn from it
# The owner kept the change ("Use this"): the chain's own learnings loop (run-kit learnings.py) gets it, so the next
# piece starts from it. Each kept line is a candidate (in force once the same fix shows in a second run); each ask's
# lesson is a candidate too, in force at once when he stated it as a standing rule. His words stay in his own node.
STATIONS = {"video": {"cast": ["writing", "video"], "look": ["writing", "video"]},
            "email": {"brief": ["copy", "image"]}}
DEFAULT_STATION = {"video": ["writing"], "email": ["copy"]}


def stations_for(piece_type, owner):
    return STATIONS.get(piece_type, {}).get(owner) or DEFAULT_STATION.get(piece_type, ["writing"])


def _ln():
    kit = str(COMPONENTS / "run-kit")
    if kit not in sys.path:
        sys.path.append(kit)
    os.environ.setdefault("AI_WORKSPACE", str(WS))
    from run_kit import learnings as LN
    return LN


def learn(rec):
    """Hand a kept revision to the chain's learnings. Returns what was filed: [{id, rule, promoted, from}]."""
    LN, out = _ln(), []
    brand, run = rec["brand"], Path(rec["run"]).name
    owner_of = {f: a.get("owner") for a in rec.get("asks") or [] for f in a.get("files") or []}
    for e in rec.get("edits") or []:
        st = stations_for(rec["piece_type"], owner_of.get(e["file"]))[0]
        for r in LN.capture(brand, st, e["find"], e["replace"], run=run, file=e["file"], by="owner",
                            said=e.get("quote") or ""):
            out.append({"id": r["id"], "rule": r["rule"], "promoted": r.get("promoted", False), "from": "kept edit"})
    for a in rec.get("asks") or []:
        lesson = (a.get("lesson") or "").strip()
        if not lesson:
            continue
        r = LN.note(brand if a.get("brand_only") else None, stations_for(rec["piece_type"], a.get("owner")), lesson,
                    kind=a.get("lesson_kind") if a.get("lesson_kind") in ("do", "never") else "do", run=run,
                    file=",".join(a.get("files") or []), src="revision", by="owner", said=a.get("quote") or "",
                    said_rule=bool(a.get("rule_said")))
        out.append({"id": r["id"], "rule": lesson, "promoted": r.get("promoted", False), "from": "lesson",
                    "rule_said": bool(a.get("rule_said")), "stations": r["stations"]})
    return out


# ------------------------------------------------------------------ use it
def stage_check(where):
    sc = COMPONENTS / "stage-check" / "stage_check.py"
    if not sc.is_file():
        return {"ran": False, "why": "the stage check is not here"}
    ref = where["run"].name
    try:
        r = subprocess.run([sys.executable, str(sc), ref], cwd=str(WS), capture_output=True, text=True, timeout=600)
    except (subprocess.SubprocessError, OSError) as e:
        return {"ran": False, "why": str(e)[:200]}
    tail = [x for x in ((r.stdout or "") + (r.stderr or "")).strip().splitlines() if x.strip()][-12:]
    return {"ran": True, "exit": r.returncode, "tail": tail}


def use(brand, nid, say=print):
    """The owner's "Use this": the revised files go in place; each old one is kept as <name>.before-rev-<id>.md."""
    n = note(brand, nid)
    recp = WS / (n.get("revision") or "")
    rec = read_json(recp) if n.get("revision") else None
    if not rec or not rec.get("files"):
        raise ValueError("this note has no revision to use")
    if rec.get("in_use"):
        return rec
    run = WS / rec["run"]
    out = recp.parent
    for f in rec["files"]:
        live = run / f
        if live.read_text(errors="replace") != (out / "before" / f).read_text(errors="replace"):
            raise ValueError("%s changed since this revision was made: revise again" % f)
    kept = []
    for f in rec["files"]:
        live = run / f
        old = live.with_name(live.stem + ".before-rev-" + rec["id"] + live.suffix)
        shutil.copy2(live, old)
        tmp = live.with_name(live.name + ".rev-tmp")
        tmp.write_text((out / "after" / f).read_text(errors="replace"))
        os.replace(tmp, live)
        kept.append(rel(old))
        say("in place: %s (old kept as %s)" % (f, old.name))
    where = {"type": rec["piece_type"], "run": run}
    rec.update(in_use=True, used_at=now(), state="in use", old_versions=kept,
               stage_check=stage_check(where) if rec["piece_type"] == "video" else {"ran": False, "why": "no lane"})
    try:
        rec["learned"] = learn(rec)
    except Exception as e:  # noqa: BLE001 -- a store that will not write never undoes his kept change
        rec["learned_error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
    say("learned: %d candidate(s), %d now in force" % (len(rec.get("learned") or []),
                                                       sum(1 for x in rec.get("learned") or [] if x["promoted"])))
    write_json(recp, rec)
    (out / "why.md").write_text(why_md(rec))
    mark(brand, nid, state="in use", revision_view=view(rec))
    return rec


# ------------------------------------------------------------------ the Studio's job and the nightly run
def result_md(rec):
    v = view(rec)
    L = ["%s" % (rec.get("summary") or rec.get("read") or rec["state"]), "",
         "| | |", "|---|---|", "| Piece | %s |" % (rec.get("title") or rec["item"]), "| State | %s |" % rec["state"],
         "| Checks | %s |" % ({True: "pass", False: "held: " + str(v["why_held"]), None: "—"}[v["passed"]]),
         "| Record | `%s` |" % v["record"], ""]
    for c in v["changes"]:
        L += ["**%s** · %s" % (c["file"], c["why"]), "", "> “%s”" % (c["quote"] or ""), "",
              "Before: %s" % c["before"].strip().replace("\n", " ")[:300],
              "", "After: %s" % c["after"].strip().replace("\n", " ")[:300], ""]
    return "\n".join(L)


def meter_line(rec):
    """One stream-json style `result` line, so the Studio's job meter counts what this revision cost."""
    tok_in = sum(m.get("tokens_in") or 0 for m in rec.get("meter") or [])
    tok_out = sum(m.get("tokens_out") or 0 for m in rec.get("meter") or [])
    return json.dumps({"type": "result", "result": rec.get("summary") or rec["state"], "total_cost_usd": rec.get("cost_usd"),
                       "usage": {"input_tokens": tok_in, "output_tokens": tok_out},
                       "modelUsage": {rec["model"]: {}}, "num_turns": len(rec.get("meter") or []),
                       "duration_ms": 1000 * sum(m.get("seconds") or 0 for m in rec.get("meter") or [])})


def cmd_ask(a):
    text = a.input.strip()
    use_it = text.lower().startswith("use ")
    nid = text.split()[-1]
    rec = use(a.brand, nid) if use_it else revise(a.brand, nid)
    if a.out:
        Path(a.out).write_text(result_md(rec) + "\n")
    print(meter_line(rec))
    return 0


def cmd_run(a):
    if a.note:
        ids = [a.note]
    else:
        ids = [n["id"] for n in notes(a.brand) if n.get("state") == "new"][: a.max]
    if not ids:
        print("no new notes for %s" % a.brand)
        return 3
    bad = 0
    for nid in ids:
        try:
            rec = revise(a.brand, nid, dry=a.dry_run)
            print("%s  %-18s %d change(s) · checks %s · $%.2f · runs/revision/%s/%s" % (
                nid, rec["state"], len(rec["edits"]), rec["checks"].get("passed"), rec.get("cost_usd") or 0,
                a.brand, rec["id"]))
        except (ValueError, RuntimeError) as e:
            bad += 1
            print("%s  not revised: %s" % (nid, e))
    return 1 if bad and bad == len(ids) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="do", required=True)
    for name in ("list", "run", "use", "show", "ask"):
        p = sub.add_parser(name)
        p.add_argument("--brand", required=True)
        if name in ("run", "use", "show"):
            p.add_argument("--note", required=name != "run")
        if name == "run":
            p.add_argument("--all-new", action="store_true")
            p.add_argument("--max", type=int, default=10)
            p.add_argument("--dry-run", action="store_true", help="write the record only; the note stays new")
        if name == "ask":
            p.add_argument("--input", required=True)
            p.add_argument("--out")
    a = ap.parse_args(argv)
    if not SAFE.match(a.brand):
        raise SystemExit("bad brand")
    if a.do == "list":
        for n in notes(a.brand):
            if n.get("state") == "new":
                print("%s  %s  %s  %s" % (n["id"], n.get("item"), "tella" if n.get("tella") else "typed",
                                          (n.get("text") or "")[:80].replace("\n", " ")))
        return 0
    if a.do == "run":
        if not a.note and not a.all_new:
            raise SystemExit("name a --note or say --all-new")
        return cmd_run(a)
    if a.do == "use":
        rec = use(a.brand, a.note)
        print("in use: %s · stage check %s" % (", ".join(rec["files"]), (rec.get("stage_check") or {}).get("exit")))
        return 0
    if a.do == "show":
        n = note(a.brand, a.note)
        print(json.dumps(read_json(WS / n["revision"]) if n.get("revision") else n, indent=1, ensure_ascii=False))
        return 0
    return cmd_ask(a)


if __name__ == "__main__":
    sys.exit(main())
