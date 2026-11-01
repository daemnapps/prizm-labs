"""Feedback — the brand's own feedback-form answers into the avatar's bank.

    python3 components/research-gatherer/gather.py feedback --brand B [--dry-run] [--since ISO] [--include-tests]

Built 2026-09-29. The forms are components/feedback-forms: one page per brand,
every customer stage, each submission ONE Klaviyo event (metric "Submitted
Feedback") carrying the stage, the form version and every question with its
answer. This mode reads those events back through the Klaviyo private API
(the key named in the brand's config, read by NAME — environment first, then
the Keychain) and turns every OPEN-TEXT answer into a bank row:

  source id   survey_<brand>_feedback-<stage>          (the Naming Standard's survey kind)
  question    q-<nn>_<question>                         (nn = the question's own number in the config)
  item        the Klaviyo event id                      (the profile and its email are never read into a row)
  lane        from the STAGE, by relationship — never guessed from the words:
              list/checkout stages -> leads; customer stages -> customers (churned when the
              words exit); refund -> churned; cancelled subscription -> churned/subscriber
  feedback    {stage, areas, yields, form_version, question_id, taps}   — the business areas the
              question serves and every tap answer from the same submission, so the bank can be
              searched by stage and by business area (language-layer query --area / --feedback-stage)

Tap answers (choices, scales) are not language; they ride on each row of the
same submission as `feedback.taps`, and a 0–10 / 1–5 score as `signal.rating`.
Events marked test=true are skipped unless --include-tests (the end-to-end
proof). Cursor: runs/research/<brand>/feedback-state.json, the newest event
time, moved only when nothing is held.

What a brand pulls is its own config: `operations/language-pulls.json` ›
`feedback` ({"enabled", "key", "metric", "since"}) plus
`operations/feedback-stages.json` / `feedback-questions.json`. A brand whose
key is missing is named in the run's notes, never guessed around.
"""
import argparse
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
import urllib.error

from . import annotate as A
from . import engine
from . import voicepull as V

say = V.say
API = "https://a.klaviyo.com/api/"
REVISION = "2025-10-15"
EMPTY = {"", "n/a", "na", "no", "none", "nope", "nothing", "-", ".", "no comment", "no comments",
         "nothing else", "not at all", "idk", "nah"}
SCORE_TYPES = ("scale",)


def forms(brand):
    """(stages by id, questions by stage) from the brand's feedback config, or ({}, {})."""
    d = engine.WORKSPACE / "brands" / brand / "operations"
    try:
        st = json.loads((d / "feedback-stages.json").read_text())
        qs = json.loads((d / "feedback-questions.json").read_text())
    except Exception:
        return {}, {}
    return {s["stage"]: s for s in st.get("stages", [])}, qs.get("stages", {})


def qslug(q, n=60):
    s = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (q or "").lower())).strip("-")
    return s[:n].rstrip("-")


def relationship_for(stage_cfg):
    """(relationship, force_lane) for rows from this stage — the stage decides,
    by relationship; the words never move a lead into customers."""
    lane = stage_cfg.get("lane")
    force = stage_cfg.get("force_lane")
    if lane in ("customer", "churned"):
        return "ordered", force
    return stage_cfg.get("relationship") or "list-member", force or lane or "lead"


def rows_from_events(events, brand, stages, questions, today, include_tests=False):
    """Klaviyo events -> (rows, newest event time, skipped). Pure — the tests call it.

    `events` are Klaviyo API event resources ({id, attributes: {datetime,
    event_properties}}). Only open-text answers become rows."""
    rows, newest, skipped = [], None, {"test": 0, "other brand": 0, "unknown stage": 0}
    for ev in events:
        at = ev.get("attributes") or {}
        p = at.get("event_properties") or {}
        when = at.get("datetime") or ""
        newest = max(newest, when) if newest else when
        if p.get("brand") and p.get("brand") != brand:
            skipped["other brand"] += 1
            continue
        if p.get("test") and not include_tests:
            skipped["test"] += 1
            continue
        stage = p.get("stage")
        scfg = stages.get(stage)
        if not scfg:
            skipped["unknown stage"] += 1
            continue
        qcfg = {q["id"]: q for q in (questions.get(stage) or {}).get("questions", [])}
        rel, force = relationship_for(scfg)
        answers = p.get("answers") or []
        taps, rating = {}, None
        for a in answers:
            q = qcfg.get(a.get("id")) or {}
            typ = q.get("type") or a.get("type")
            if typ != "text":
                taps[a.get("id")] = a.get("answer") if not a.get("other") else f"{a.get('answer')}: {a.get('other')}"
                if typ in SCORE_TYPES and isinstance(a.get("answer"), (int, float)) and rating is None:
                    rating = a.get("answer")
        eid = ev.get("id")
        said = when[:10]
        for a in answers:
            q = qcfg.get(a.get("id")) or {}
            typ = q.get("type") or a.get("type")
            text = a.get("other") if typ in ("choice", "multi") and a.get("other") else (a.get("answer") if typ == "text" else None)
            if not isinstance(text, str):
                continue
            text = text.strip()
            if len(text) < 3 or re.sub(r"[^a-z ]", "", text.lower()).strip() in EMPTY:
                continue
            qtext = q.get("text") or a.get("question") or a.get("id")
            n = q.get("n") or a.get("n") or 0
            qid = f"q-{int(n):02d}_{qslug(qtext)}"
            sid = f"survey_{brand}_feedback-{stage}"
            rows.append(dict(
                kind="survey", text=A.clean(text), said=said, pulled=today,
                ref=f"klaviyo-event:{eid}#{qid.split('_')[0]}", item=eid,
                source_name=f"Feedback form · {scfg.get('label') or stage} — Q: {qtext}",
                source_type="survey", source_id=sid, source_kind="survey", property=brand,
                question=qid, relationship=rel, force_lane=force, rating=rating,
                feedback={"stage": stage, "areas": q.get("areas") or a.get("areas") or [],
                          "yields": q.get("yields") or a.get("yields") or [],
                          "form_version": p.get("form_version"), "question_id": a.get("id"),
                          "taps": dict(taps), **({"test": True} if p.get("test") else {})}))
    return rows, newest, skipped


# ---------------------------------------------------------------- Klaviyo, read only

def _get(url, key):
    r = urllib.request.Request(url, headers={"Authorization": f"Klaviyo-API-Key {key}", "revision": REVISION,
                                             "accept": "application/vnd.api+json"})
    with urllib.request.urlopen(r, timeout=60) as f:
        return json.loads(f.read().decode())


def fetch_events(key_name, metric, since):
    """(events, None) or (None, why). Every event of `metric` after `since`, oldest first."""
    key = V.key(key_name)
    if not key:
        return None, f"{key_name} not found (environment or Keychain)"
    try:
        url = API + "metrics/?fields[metric]=name"
        mid = None
        while url and not mid:
            d = _get(url, key)
            mid = next((m["id"] for m in d.get("data", []) if m["attributes"].get("name") == metric), None)
            url = (d.get("links") or {}).get("next")
        if not mid:
            return [], None   # nobody has submitted yet: the metric appears with the first event
        flt = f'equals(metric_id,"{mid}")'
        if since:
            since = since if "T" in since else since + "T00:00:00+00:00"
            flt += f",greater-than(datetime,{since})"
        url = API + "events/?" + urllib.parse.urlencode({"filter": flt, "sort": "datetime", "page[size]": "200",
                                                         "fields[event]": "datetime,event_properties"})
        out = []
        while url:
            d = _get(url, key)
            out += d.get("data", [])
            url = (d.get("links") or {}).get("next")
        return out, None
    except urllib.error.HTTPError as e:
        return None, f"Klaviyo refused ({e.code}) — check the key's scopes (events:read, metrics:read)"
    except Exception as e:
        return None, str(e)[:160]


def main(argv=None, fetch=None, labeller=None, claude=None):
    ap = argparse.ArgumentParser(prog="gather.py feedback")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar")
    ap.add_argument("--since", help="ISO time; default = the cursor, else `since` in language-pulls.json › feedback")
    ap.add_argument("--dry-run", action="store_true", help="pull and show the rows; read and file nothing")
    ap.add_argument("--include-tests", action="store_true", help="keep events marked test=true (the end-to-end proof)")
    a = ap.parse_args(argv)
    fetch = fetch or fetch_events
    c = V.cfg("feedback")
    bj = V.brand_json(a.brand)
    label = bj.get("label") or a.brand
    fb = bj.get("feedback") or {}
    now, today, run_label = V.now_labels()
    say(f"feedback · {a.brand}{' · DRY RUN' if a.dry_run else ''}")
    if not fb.get("enabled"):
        say(f"  feedback: MISSING — {fb.get('why') or 'not switched on in language-pulls.json › feedback'}"
            if fb else "  no feedback block in language-pulls.json — nothing to pull")
        return 0
    stages, questions = forms(a.brand)
    if not stages:
        say(f"  feedback: MISSING — no operations/feedback-stages.json / feedback-questions.json for {a.brand}")
        return 0
    avatar = V.avatar_for(a.brand, bj, a.avatar)
    if not avatar:
        say("  name the avatar (--avatar, or language_avatar in language-pulls.json)")
        return 2
    state = V.load_state(a.brand, "feedback")
    since = a.since or state.get("last_event") or fb.get("since")
    events, why = fetch(fb.get("key"), fb.get("metric") or "Submitted Feedback", since)
    if events is None:
        say(f"  feedback: MISSING — {why}")
        return 0
    rows, newest, skipped = rows_from_events(events, a.brand, stages, questions, today, a.include_tests)
    skip = ", ".join(f"{v} {k}" for k, v in skipped.items() if v)
    say(f"  {len(events)} submissions since {since or 'the start'} · {len(rows)} open answers"
        + (f" · skipped {skip}" if skip else ""))
    if a.dry_run:
        for r in rows:
            f = r["feedback"]
            say(f"    [{r['source_id']} · {r['question']} · lane {r['force_lane'] or ('customer' if r['relationship'] == 'ordered' else r['relationship'])} (by relationship) · "
                f"areas {','.join(f['areas'])}{' · TEST' if f.get('test') else ''}] {r['text'][:110]}")
    fresh, filed, dropped, held = V.file_rows(a.brand, avatar, label, rows, "feedback form answers", c, run_label,
                                              a.dry_run, labeller=labeller, claude=claude)
    if filed is None:
        say("  dry run — nothing read, nothing filed" if a.dry_run else "  nothing new")
        if not a.dry_run and newest:
            state["last_event"] = newest
            V.save_state(a.brand, "feedback", state)
        return 0
    V.write_run(a.brand, "feedback", label, run_label, since or "the start", filed, dropped, held, [],
                extra={"avatar": avatar, "submissions": len(events), "skipped": skipped},
                intro="New answers to the brand's own feedback forms since the last run. Every row below is now in "
                      "the brand's language bank, with its stage, the business areas it serves, its lane, awareness "
                      "level and sophistication signal.")
    if not held and newest:
        state["last_event"] = newest
        V.save_state(a.brand, "feedback", state)
    return 0
