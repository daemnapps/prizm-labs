#!/usr/bin/env python3
"""The feedback forms' language pass — every question, tap option and stage
email worded from the brand's language bank, through the language layer.

    python3 components/feedback-forms/language_pass.py --brand <brand> [--write]

Reads   runs/feedback-forms/<brand>/language-pass-2026-09-29/draft.json
        (the queries this pass runs, and the wording written from what they returned)
Runs    every query through components/language-layer (engine.load / engine.query /
        engine.for_stage — the same code query_language.py runs), never a grep
Writes  runs/feedback-forms/<brand>/language-pass-2026-09-29/
            before.json     the brand's feedback-questions.json as it was before this pass (kept once)
            queries.json    every query, its filters, how many rows matched, the ids returned
            queries.md      the same, readable, plus each stage's for_stage block
            coverage.json   per stage: questions, taps, how many cite bank lines
            used-proposal.json   the used-lane record these surveys would add (see below)
        and with --write, a PROPOSAL in the same run folder: deliverable/feedback-questions.json
        (the wording, with language_used ids on every question, tap option and email) and
        PROPOSAL.md (its brands/ target and one sha-guarded copy line). brands/ is never
        written: the brand's feedback-questions.json is read, and a person commits the
        proposal (K2 (brands write wall), 2026-10-06).

Tap options are not picked by hand: each option names the words that make it
(`theme`), the pass runs that as a `contains` query inside the question's lane
and tags, and the option cites the rows it returned, loudest first — the
engine's own repeat count ("said N× in this bank") and the number of rows in
the lane that say it. Question and email wording cite the rows written from
(`language_used`); every cited id must be one a query of this pass returned,
or the pass stops.

The used lane: `gather.py apply --proposal` (research-gatherer bank_apply.py)
can only re-point row ids inside used-lane files that already exist and write
no whole file but the source registry, so it cannot add a new used-lane file.
This pass therefore writes the record as a proposal under runs/ and does not
write brands/<brand>/core-avatars/ at all.
"""
import argparse
import copy
import datetime as dt
import difflib
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WS / "components" / "language-layer"))
from language_layer import engine as E  # noqa: E402

E.configure(workspace=WS)
RUN = "language-pass-2026-09-29"
BIG = 100000
# Lines a page must not carry even redacted: a signature, an order or invoice
# number, a phone or address placeholder. An option never cites one of these;
# a hand-cited one stops the pass.
PII_HINTS = ("ceo", "ph.d", "@", "[phone]", "[address]", "[email]", "order [number]", "invoice [number]", "[order]", "order #")
SIGNED = re.compile(r"(\n\s*[A-Z][a-z]+ [A-Z][a-z]+\s*$)|(\b[Mm]y (?:[Ss]on|[Dd]aughter|[Ww]ife|[Hh]usband|[Bb]rother|[Ss]ister|[Cc]ousin|[Ff]riend) [A-Z][a-z]+)")


def pii(text):
    t = (text or "").lower()
    return any(h in t for h in PII_HINTS) or bool(SIGNED.search(text or ""))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def lane_rows(rows, q):
    fs = q.get("files")
    return [r for r in rows if not fs or r.get("_file") in fs]


def run_query(rows, q):
    """One query through the engine. `contains` (a list) runs once per term and
    the results are pooled — the engine's own `contains` filter, term by term."""
    base = dict(use=q.get("use"), funnel=q.get("funnel"), awareness=q.get("awareness"),
                topics=q.get("topics"), speaker=q.get("speaker"))
    pool = lane_rows(rows, q)
    got, seen = [], set()
    for t in (q.get("contains") or [None]):
        for r in E.query(pool, contains=t, limit=BIG, **base):
            if r["id"] not in seen:
                seen.add(r["id"])
                got.append(r)
    if q.get("exclude"):
        bad = [x.lower() for x in q["exclude"]]
        got = [r for r in got if not any(b in (r.get("text") or "").lower() for b in bad)]
    got.sort(key=lambda r: -(r.get("_repeats") or 1))
    return got


def citable(got):
    return [r for r in got if not pii(r.get("text"))]


def cli(brand, avatar, q):
    """The query_language.py line closest to this query (the CLI has no
    contains / file filter; those run through engine.query in this pass)."""
    bits = [f"python3 components/language-layer/query_language.py --brand {brand} --avatar {avatar}"]
    if q.get("funnel"):
        bits.append(f"--funnel {q['funnel']}")
    if q.get("awareness"):
        bits.append(f"--awareness {q['awareness']}")
    if q.get("use"):
        bits.append(f"--profile runs/feedback-forms/{brand}/{RUN}/profile.json --stage {q['id']}")
    return " ".join(bits)


def row_view(r):
    aw = r.get("awareness") if isinstance(r.get("awareness"), dict) else {}
    src = r.get("source") or {}
    text = (r.get("text") or "").strip()
    if pii(text):
        text = "(withheld here — the line carries a name, signature or contact placeholder; read it in the bank)"
    return {"text": text, "said": r.get("_repeats") or 1, "lane": r.get("funnel"),
            "file": r.get("_file"), "use": E.uses(r), "awareness": aw.get("level"),
            "source": src.get("name"), "source_type": src.get("type"), "source_date": src.get("date")}


def propose(brand, cfg_path, cfg, out, root=None):
    """The new wording as a proposal in the run folder — never written into
    brands/ (K2 (brands write wall)). Writes out/deliverable/feedback-questions.json
    and out/PROPOSAL.md (the target, and one copy line that refuses when the
    target is no longer what this run read); returns (the proposal's path, a
    unified diff of the brand file against it)."""
    root = Path(root or WS)
    cfg_path, out = Path(cfg_path), Path(out)
    text = json.dumps(cfg, indent=1, ensure_ascii=False) + "\n"
    path = out / "deliverable" / "feedback-questions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    old = cfg_path.read_text() if cfg_path.is_file() else ""
    rel = lambda p: p.relative_to(root).as_posix() if root in p.parents else str(p)
    here, there = rel(path), rel(cfg_path)
    if not cfg_path.is_file():
        state, guard = "new", "test ! -e %s" % shlex.quote(there)
    elif old == text:
        state, guard = "already in brands/", None
    else:
        sha = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
        state, guard = "replaces", 'test "$(shasum -a 256 < %s | cut -c1-64)" = %s' % (shlex.quote(there), sha)
    L = ["# Feedback questions proposal — %s · %s" % (brand, out.name), "",
         "Made %s by components/feedback-forms/language_pass.py --write." % dt.date.today().isoformat(),
         "Nothing here is in brands/ yet: the language pass never writes there (K2 (brands",
         "write wall), 2026-10-06). A person checks the file, copies it with the command",
         "below, and commits it as their own.", "",
         "| File in this run | Target | State |", "|---|---|---|",
         "| %s | %s | %s |" % (here, there, state), ""]
    if guard:
        L += ["Copy, from the workspace root. The line copies only while the target is still",
              "what this run read, and prints STALE otherwise:", "", "```sh",
              '%s && cp %s %s || echo "STALE: %s changed since this run; re-run language_pass.py --write"'
              % (guard, shlex.quote(here), shlex.quote(there), there),
              "```", "", "Then commit as yourself: `git add %s && git commit`" % shlex.quote(there)]
    else:
        L += ["The target already says exactly this; nothing to copy."]
    (out / "PROPOSAL.md").write_text("\n".join(L) + "\n")
    diff = "".join(difflib.unified_diff(old.splitlines(True), text.splitlines(True),
                                        fromfile=there, tofile=here))
    return path, diff


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--write", action="store_true",
                    help="writes a PROPOSAL into the run folder; brands/ is never written")
    a = ap.parse_args(argv)
    out = WS / "runs" / "feedback-forms" / a.brand / RUN
    draft = json.loads((out / "draft.json").read_text())
    brand, avatar = draft["brand"], draft["avatar"]
    rows = E.load(brand, avatar)
    by_id = {r["id"]: r for r in rows}

    # the feedback chain's stage map, as a query_language.py --profile file
    prof = {"title": "Customer language for this feedback stage", "widen": "ladder",
            "stage_use": {q["id"]: q["use"] for q in draft["queries"] if q.get("use")}}
    prof["stage_use"].update(draft.get("stage_use") or {})
    (out / "profile.json").write_text(json.dumps(prof, indent=1, ensure_ascii=False) + "\n")

    queries, keep = [], {}
    returned_by_stage = {}

    def record(q, got, stage):
        ids = [r["id"] for r in got]
        for r in got[:30]:
            keep[r["id"]] = r
        queries.append(dict(id=q["id"], stage=stage, purpose=q.get("purpose", ""), avatar=avatar,
                            funnel=q.get("funnel"), files=q.get("files"), use=q.get("use"),
                            awareness=q.get("awareness"), contains=q.get("contains"), exclude=q.get("exclude"),
                            matched=len(ids), returned=ids[:500], cli=cli(brand, avatar, q),
                            engine=f"engine.query(engine.load('{brand}', '{avatar}'), use={q.get('use')}, "
                                   f"funnel={q.get('funnel')!r}, awareness={q.get('awareness')!r}, "
                                   f"contains=<each of {q.get('contains')}>)"))
        for st in (stage if isinstance(stage, list) else [stage]):
            returned_by_stage.setdefault(st, set()).update(ids[:500])
        return got

    qdef = {}
    for q in draft["queries"]:
        qdef[q["id"]] = q
        record(q, run_query(rows, q), q.get("stages") or q.get("stage") or "all")

    # each stage's for_stage block — the call query_language.py makes
    blocks = {}
    for sid, lane in (draft.get("stage_lanes") or {}).items():
        smap = {sid: lane["use"]}
        txt = E.for_stage(brand, sid, avatar, funnel=lane.get("funnel"), limit=lane.get("limit", 20),
                          stage_use=smap, widen="ladder", title="Customer language for this feedback stage",
                          awareness=lane.get("awareness"))
        ids = re.findall(r"\[(language_[^\]]+)\]", txt)
        for i in ids:
            if i in by_id and pii(by_id[i].get("text")):
                txt = txt.replace((by_id[i].get("text") or "").strip(), "(withheld here — the line carries a name, signature or contact placeholder)")
        blocks[sid] = dict(funnel=lane.get("funnel"), use=lane["use"], awareness=lane.get("awareness"), ids=ids,
                           cli=f"python3 components/language-layer/query_language.py --brand {brand} --avatar {avatar}"
                               + (f" --funnel {lane['funnel']}" if lane.get("funnel") else "")
                               + (f" --awareness {lane['awareness']}" if lane.get("awareness") else "")
                               + f" --profile runs/feedback-forms/{brand}/{RUN}/profile.json --stage {sid} --limit {lane.get('limit', 20)}",
                           block=txt)
        prof["stage_use"][sid] = lane["use"]
        returned_by_stage.setdefault(sid, set()).update(ids)
        for i in ids:
            if i in by_id:
                keep[i] = by_id[i]
    (out / "profile.json").write_text(json.dumps(prof, indent=1, ensure_ascii=False) + "\n")

    # the wording
    cfg_path = WS / "brands" / brand / "operations" / "feedback-questions.json"
    cfg = json.loads(cfg_path.read_text())
    # the wording before this pass — frozen in the run folder, so a re-run
    # still compares against what the forms said before the bank was used
    before = out / "before.json"
    if not before.exists():
        before.write_text(cfg_path.read_text())
    old = json.loads(before.read_text())
    problems, cover, used = [], {}, []

    def allowed(stage):
        return returned_by_stage.get(stage, set()) | returned_by_stage.get("all", set())

    def cite(ids, stage, where, text_for=None):
        ok = allowed(stage)
        for i in ids:
            if i not in by_id:
                problems.append(f"{where}: {i} is not a row in the bank")
            elif i not in ok:
                problems.append(f"{where}: {i} was not returned by any query of this stage")
            elif pii(by_id[i].get("text")):
                problems.append(f"{where}: {i} carries a signature / order number / contact placeholder — cite another line")
            else:
                keep[i] = by_id[i]
                used.append(dict(row_id=i, text=(by_id[i].get("text") or "").strip(), where=where, how="cited", results=None))

    for sid, st in draft["stages"].items():
        was_st = old["stages"].get(sid, {})
        was_q = {q["id"]: q for q in was_st.get("questions", [])}
        new_st = {k: v for k, v in st.items() if k not in ("questions", "email")}
        cite(st.get("title_language_used", []), sid, f"{sid}/title")
        nq = []
        c = dict(questions=0, questions_citing=0, taps=0, taps_citing=0, rows_queried=0)
        for q in st["questions"]:
            q = copy.deepcopy(q)
            src = was_q.get(q.pop("was_id", q["id"]))
            if src and src.get("text") != q["text"]:
                q["was"] = src["text"]
            elif src:
                q["was"] = src["text"]
            else:
                q["was"] = None
            if src and src.get("options"):
                q["was_options"] = src["options"]
            if src and src.get("options") and q.get("options") is None and q["type"] in ("choice", "multi"):
                problems.append(f"{sid}/{q['id']}: a tap with no options")
            cite(q.get("language_used", []), sid, f"{sid}/{q['id']}")
            if q.get("language_used"):
                c["questions_citing"] += 1
            c["questions"] += 1
            if q.get("options") and isinstance(q["options"][0], dict):
                labels, ol = [], []
                for o in q["options"]:
                    labels.append(o["label"])
                    c["taps"] += 1
                    bq = o.get("query") or q.get("language_query")
                    base = qdef.get(bq)
                    if o.get("theme") and not base:
                        problems.append(f"{sid}/{q['id']}: option {o['label']!r} needs a query (the lane + tags it comes from)")
                        continue
                    if o.get("theme"):
                        oq = dict(base, id=f"{bq}/{slug(o['label'])}", contains=o["theme"],
                                  exclude=o.get("exclude"), purpose=f"tap option “{o['label']}” — {sid}/{q['id']}")
                        got = record(oq, run_query(rows, oq), sid)
                        ids = [r["id"] for r in citable(got)[:o.get("cite", 5)]]
                        if not got:
                            problems.append(f"{sid}/{q['id']}: option {o['label']!r} matched no rows")
                        cite(ids, sid, f"{sid}/{q['id']}/option")
                        ol.append(dict(option=o["label"], theme=o["theme"], query=oq["id"], rows=len(got),
                                       said=(got[0].get("_repeats") or 1) if got else 0,
                                       top=row_view(citable(got)[0])["text"] if citable(got) else None, language_used=ids))
                        if ids:
                            c["taps_citing"] += 1
                    else:
                        ids = o.get("language_used") or []
                        cite(ids, sid, f"{sid}/{q['id']}/option")
                        ol.append(dict(option=o["label"], theme=None, query=None, rows=len(ids),
                                       said=max([by_id[i].get("_repeats") or 1 for i in ids if i in by_id] or [0]),
                                       top=None, language_used=ids, note=o.get("note")))
                        if ids:
                            c["taps_citing"] += 1
                q["options"] = labels
                q["options_language"] = ol
            elif q.get("options"):
                c["taps"] += len(q["options"])
            nq.append(q)
        em = copy.deepcopy(st["email"])
        cite(em.get("language_used", []), sid, f"{sid}/email")
        new_st["questions"] = nq
        new_st["email"] = em
        new_st["was"] = {"title": was_st.get("title"), "intro": was_st.get("intro"),
                         "email": {k: was_st.get("email", {}).get(k) for k in ("subject", "preview", "body", "button")}}
        c["rows_queried"] = len(allowed(sid))
        c["email_citing"] = bool(em.get("language_used"))
        c["language_note"] = st.get("language_note")
        cover[sid] = c
        cfg["stages"][sid] = new_st

    # every id E.query saw with its repeat count — the page's "from the bank" lines
    rows_out = {i: row_view(r) for i, r in keep.items()}
    rec = dict(kind="feedback-forms-language-pass", brand=brand, avatar=avatar, run=f"runs/feedback-forms/{brand}/{RUN}",
               date=draft.get("date"), engine="components/language-layer/language_layer/engine.py",
               bank_rows=len(rows), note=draft.get("note"), queries=queries,
               stage_blocks={k: {x: v[x] for x in v if x != "block"} for k, v in blocks.items()}, rows=rows_out)
    (out / "queries.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    (out / "coverage.json").write_text(json.dumps(cover, indent=1, ensure_ascii=False) + "\n")

    L = [f"# {cfg.get('label', brand)} feedback forms — language pass, {draft.get('date')}", "",
         f"Every query this pass ran through the language layer (`engine.load` → `engine.query` / `engine.for_stage`) "
         f"over the **{avatar}** bank ({len(rows):,} rows), and the row ids it returned. The wording in "
         f"`brands/{brand}/operations/feedback-questions.json` cites these ids (`language_used`). "
         f"Re-run: `python3 components/feedback-forms/language_pass.py --brand {brand}`.", ""]
    if draft.get("note"):
        L += [draft["note"], ""]
    L += ["## Coverage", "", "| Stage | Rows queried | Questions | Questions citing bank lines | Taps | Taps citing | Email cites | Note |",
          "|---|---|---|---|---|---|---|---|"]
    for sid, c in cover.items():
        L.append(f"| {sid} | {c['rows_queried']} | {c['questions']} | {c['questions_citing']} | {c['taps']} | {c['taps_citing']} | "
                 f"{'yes' if c['email_citing'] else 'no'} | {c['language_note'] or ''} |")
    L += ["", "## Each stage's for_stage block", ""]
    for sid, b in blocks.items():
        L += [f"### {sid}", "", f"`{b['cli']}`", "", b["block"], ""]
    L += ["## Every query", ""]
    for q in queries:
        L += [f"### `{q['id']}` — {q['purpose']}", "",
              f"lane `{q['funnel'] or 'any'}`" + (f" · files {', '.join(q['files'])}" if q.get("files") else "")
              + f" · tags {', '.join(q['use'] or ['any'])}" + (f" · awareness {q['awareness']}" if q.get("awareness") else "")
              + (f" · words containing: {' | '.join(q['contains'])}" if q.get("contains") else "")
              + (f" · minus: {' | '.join(q['exclude'])}" if q.get("exclude") else "")
              + f" · **{q['matched']} rows matched**", ""]
        for i in q["returned"][:8]:
            r = rows_out.get(i) or row_view(by_id[i])
            L.append(f"- [{i}] “{r['text'][:160]}” — said {r['said']}×")
        L.append("")
    (out / "queries.md").write_text("\n".join(L) + "\n")

    # the used-lane record, as a proposal
    target = f"brands/{brand}/core-avatars/{avatar}/language/used/feedback-forms_{brand}_2026-09-29.json"
    uniq, seen = [], set()
    for u in used:
        k = (u["row_id"], u["where"])
        if k not in seen:
            seen.add(k)
            uniq.append(u)
    content = {"schema": 1, "kind": "language-used", "asset": f"feedback-forms_{brand}_2026-09-29",
               "run": f"runs/feedback-forms/{brand}/{RUN}", "chain": "feedback-form",
               "written": "2026-09-29", "state": "drafted", "used": uniq}
    prop = {"kind": "language-used-proposal", "version": 1, "brand": brand, "tool": "feedback-forms language pass",
            "target": target, "content": content,
            "rows": len({u['row_id'] for u in uniq}), "marks": len(uniq),
            "why_a_proposal": "gather.py apply --proposal (research-gatherer bank_apply.py) only re-points row ids "
                              "inside used-lane files that already exist and writes no whole file but "
                              "core-avatars/language-sources.json, so it cannot add a new used-lane file. Nothing in "
                              "brands/<brand>/core-avatars/ was written by this pass.",
            "where_means": "<feedback stage>/<question id>[/option] or <stage>/email or <stage>/title — the feedback "
                           "chain's stages, not the video chain's 3/4b/4d/4e/4g/5"}
    (out / "used-proposal.json").write_text(json.dumps(prop, indent=1, ensure_ascii=False) + "\n")

    for p in problems:
        print("PROBLEM", p)
    tq = sum(c["questions"] for c in cover.values())
    tc = sum(c["questions_citing"] for c in cover.values())
    tt = sum(c["taps"] for c in cover.values())
    ttc = sum(c["taps_citing"] for c in cover.values())
    print(f"{brand}: {len(queries)} queries · {len(rows):,} bank rows · questions {tc}/{tq} cite · taps {ttc}/{tt} cite · "
          f"{prop['rows']} rows marked used")
    for sid, c in cover.items():
        print(f"  {sid:20} rows {c['rows_queried']:5}  q {c['questions_citing']}/{c['questions']}  taps {c['taps_citing']}/{c['taps']}"
              f"  email {'yes' if c['email_citing'] else 'NO'}{'  NOTE ' + c['language_note'][:80] if c['language_note'] else ''}")
    if problems:
        return 1
    if a.write:
        cfg["form_version"] = draft.get("form_version", cfg["form_version"])
        cfg["language_pass"] = f"runs/feedback-forms/{brand}/{RUN}"
        if draft.get("_what"):
            cfg["_what"] = draft["_what"]
        for k in ("copy", "thanks"):
            if draft.get(k):
                cfg[k] = dict(cfg[k], **draft[k])
        path, diff = propose(brand, cfg_path, cfg, out)
        print(diff, end="")
        print(f"proposal: {path.relative_to(WS)} — a person commits it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
