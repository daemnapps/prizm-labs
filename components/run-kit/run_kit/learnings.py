"""The chain's learnings: every correction so it never happens again, every win so it happens again. Any chain, any brand.

owner, 2026-10-17: "every time a shift is made on the copy level, on the image level, whatever the case may be, with
the feedback, that all needs to be stored and put into learnings back up and through the chain … it needs to
compound", and the same day: "this learning stuff should definitely be agnostic … this is for the overall chain."

Two stores, both under the repo's runs/ (a machine never writes brands/):

    runs/learnings/_all.jsonl       holds for every brand and every chain (no brand is ever named in it)
    runs/learnings/<brand>.jsonl    facts about one brand only (its product, its colours, its people)

Each line: {"at", "by", "chain", "stage", "kind", "rule", "why", "from"}
    chain   email | ads | video | page | all       (which line it came from; `all` reaches every line)
    stage   calendar | copy | design | picture | edit | build | all
    kind    do | never     (a later {"kind": "retire", "n": i} line retires rule i of that store)

Read by every stage that writes or makes something: `block(brand, stages, chain)` is the text a prompt carries.
The image engine (components/image-production) reads the `picture` rules on every picture it makes, so ads, emails
and video frames all learn from one another.

    python3 -m run_kit.learnings add  --stage picture --kind never --rule "…" --why "…" --by editor [--brand b] [--chain email]
    python3 -m run_kit.learnings list [--brand b] [--stage picture]
    python3 -m run_kit.learnings retire --n 4 --why "…" [--brand b]

THE SELF-REINFORCING LOOP (2026-11-27: every correction the owner makes is saved and handed to the next run, so each
run starts better than the last). The two stores above stay the one home of the rules IN FORCE; three things sit on top:

    stations   writing | copy | image | video | edit     a row may name several (`stations`); an old row's `stage`
               maps onto them (picture/design -> image, calendar/build -> copy/edit) and still reaches its old readers.
    candidate  runs/learnings/candidates.jsonl: what the chain made against what he kept or said (a line he edited,
               a script he locked, a call he overruled, a take finding), captured with no form for him. A candidate
               becomes a rule in force (`state: active`) when the same change recurs in a second run, or at once when
               he states it as a rule (`said_rule`). His own words never enter the repo: they are kept in his own
               node (QUOTES below), keyed by the learning's id.
    check      a rule may carry `check: {"never": [regex], "must": [regex]}`; `check_text()` flags a draft that breaks
               one before it reaches him, and the station sends it back through its own repair loop.

    every station:  handed(run_dir, station, brand)  -> the block its prompt carries, and <run>/learnings-handed.json
                                                        lists which learnings it was handed

    python3 -m run_kit.learnings capture --station writing --brand b --run R --before old.md --after kept.md
    python3 -m run_kit.learnings note    --station video --brand b --run R --rule "…" [--said "his words"] [--rule-said]
    python3 -m run_kit.learnings harvest         decision-layer overrules and take findings -> candidates; promote
    python3 -m run_kit.learnings in-force [--brand b] [--json]
"""
import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
from pathlib import Path

from . import paths

STAGES = ("calendar", "copy", "design", "picture", "edit", "build", "all",
          "writing", "image", "video")
STATIONS = ("writing", "copy", "image", "video", "edit")
# an old row's stage, read as the stations it reaches (picture rules have always fed every picture, video frames too)
STAGE_STATIONS = {"picture": ("image",), "design": ("image",), "copy": ("copy",), "calendar": ("copy",),
                  "edit": ("edit",), "build": ("edit",), "all": STATIONS}
# a station asked for by its old stage name, so old callers (`block(brand, ("picture",))`) keep working
ALIAS = {"picture": "image", "image": "picture"}


def _store(brand):
    return Path(paths.repo()) / "runs" / "learnings" / ("%s.jsonl" % (brand or "_all"))


SEED = Path(__file__).resolve().parents[1] / "learnings" / "seed.jsonl"


def _lines(f):
    rows = []
    for x in (f.read_text().splitlines() if f.is_file() else []):
        try:
            rows.append(json.loads(x))
        except ValueError:
            continue
    return rows


def load(brand=None):
    """The rules in force in one store. The shared store also carries the component's brand-free SEED
    (learnings/seed.jsonl, a definitions file that travels with the code, so a fresh copy of the workspace starts
    with what the chain already knows); a seed rule the store already holds, or retires by id, is not read twice."""
    rows = _lines(_store(brand))
    retired = {r.get("n") for r in rows if r.get("kind") == "retire"}
    gone = {r.get("id") for r in rows if r.get("kind") == "retire" and r.get("id")}
    out = [dict(r, n=i) for i, r in enumerate(rows) if r.get("kind") in ("do", "never") and i not in retired]
    if brand is None:
        have = {r.get("id") or learning_id(r["rule"]) for r in rows if r.get("rule")}
        have |= {_norm(r["rule"]) for r in rows if r.get("rule")}
        for r in _lines(SEED):
            lid = r.get("id") or learning_id(r.get("rule", ""))
            if r.get("kind") in ("do", "never") and r.get("status") != "deprecated" \
                    and lid not in have | gone and _norm(r.get("rule", "")) not in have:
                out.append(dict(r, n=None, seed=True))
    return out


# ONE-OFF EDITS ARE NOT RULES (2026-11-27): a change to one line, one section or one picture of one piece ("X became
# Y", "Moved the button section up", "<slot> picture (<what>): Remake ...") or a price/offer edit is a fix to that
# piece, not a lesson for every run. It is kept as a candidate tied to its run and never goes in force by recurring;
# only a rule someone states (said_rule) does.
ONE_OFF = re.compile(r'^(In an? [^,]+ section, ".*" became ".*"|Moved the .+ section|Cut an? .+ section|'
                     r'In the .+ section:|[\w -]+ picture \(.+\)[.:])', re.S)
PRICE = re.compile(r"[$€£]\s?\d|\b\d+% off\b|\bfree\b", re.I)


def one_off(rule):
    r = str(rule).strip()
    return bool(ONE_OFF.match(r)) or (" became " in r and bool(PRICE.search(r)))


def add(brand, stage, kind, rule, why="", by="", src="", chain="all", stations=None, run="", file="", check=None,
        lid=None, formats=None):
    if not lid and one_off(rule):                  # a piece's own edit: a candidate for that run, never in force
        return note(brand, list(STAGE_STATIONS.get(stage, (stage,))), rule, kind, run=run or src, file=file, src=src,
                    by=by, one_off=True, evidence={"why": why} if why else None)
    f = _store(brand)
    f.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": datetime.date.today().isoformat(), "by": by, "chain": chain or "all", "stage": stage, "kind": kind,
           "rule": rule.strip(), "why": (why or "").strip(), "from": src}
    if stations or run or file or check or lid or formats:
        row.update({"id": lid or learning_id(rule), "stations": list(stations or stations_of(row)), "state": "active",
                    "run": run, "file": file})
        if check:
            row["check"] = check
        if formats:
            row["formats"] = list(formats)
    with f.open("a") as h:
        h.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def retire(brand, n, why):
    f = _store(brand)
    with f.open("a") as h:
        h.write(json.dumps({"at": datetime.date.today().isoformat(), "kind": "retire", "n": n, "why": why}) + "\n")


def rules(brand, stages, chain=None, fmt=None):
    """Every rule that reaches these stages for this brand and chain: the shared ones, then the brand's, newest first.
    A rule naming `formats` reaches only those formats (and a caller that does not know its format)."""
    want = set(stages) | {"all"} | {ALIAS[s] for s in stages if s in ALIAS}
    rows = [r for b in (None, brand) for r in load(b)
            if (r.get("stage") in want or want & set(r.get("stations") or ()))
            and (chain is None or r.get("chain", "all") in (chain, "all"))
            and (not fmt or not r.get("formats") or fmt in r["formats"])]
    rows.sort(key=lambda r: r.get("at", ""), reverse=True)
    return rows


def block(brand, stages, chain=None, extra=()):
    """The learnings as the text a prompt carries; `extra` are lines a caller adds (e.g. its own send-backs)."""
    out = list(extra) + ["- %s %s%s" % ("DO:" if r["kind"] == "do" else "NEVER:", r["rule"],
                                        (" (why: %s)" % r["why"]) if r.get("why") else "") for r in rules(brand, stages, chain)]
    return "\n".join(out) if out else "(none yet)"


# ------------------------------------------------------------------ the self-reinforcing loop (2026-11-27)

CANDIDATES = "candidates.jsonl"
RECUR = 2                       # distinct runs showing the same change before it is in force on its own


def learning_id(rule):
    return "LN-" + hashlib.sha1(_norm(rule).encode()).hexdigest()[:8]


def _norm(text):
    return " ".join(re.findall(r"[a-z0-9']+", str(text).lower()))


def stations_of(row):
    """The stations a row reaches: its own `stations`, else what its old `stage` means."""
    if row.get("stations"):
        return tuple(row["stations"])
    return STAGE_STATIONS.get(row.get("stage"), (row.get("stage"),) if row.get("stage") in STATIONS else ())


def _quotes():
    """His own words live in his own node only (direction-only rule for repos): OWNER_QUOTES, else the private
    repo's context folder when this machine has it; None on every other machine, and the quote is simply not kept."""
    env = os.environ.get("OWNER_QUOTES")
    if env:
        return Path(env)
    home = Path.home() / "devel" / "daemn" / "context"
    return home / "learnings-quotes.jsonl" if home.is_dir() else None


def keep_quote(lid, said, run=""):
    f = _quotes()
    if not f or not str(said or "").strip():
        return False
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a") as h:
        h.write(json.dumps({"id": lid, "at": datetime.date.today().isoformat(), "run": run,
                            "said": str(said).strip()[:240]}, ensure_ascii=False) + "\n")
    return True


def quotes():
    """{learning id: [his words, ...]} from his own node; {} anywhere else."""
    f = _quotes()
    out = {}
    if f and f.is_file():
        for x in f.read_text().splitlines():
            try:
                q = json.loads(x)
            except ValueError:
                continue
            out.setdefault(q.get("id"), []).append(q.get("said"))
    return out


def _cand_file():
    return Path(paths.repo()) / "runs" / "learnings" / CANDIDATES


def candidates():
    f = _cand_file()
    rows = []
    for x in (f.read_text().splitlines() if f.is_file() else []):
        try:
            rows.append(json.loads(x))
        except ValueError:
            continue
    return rows


def in_force(brand=None):
    """Every rule in force for a brand (shared first, then the brand's), newest first, each with its id and stations."""
    out = []
    for b in (None, brand) if brand else (None,):
        for r in load(b):
            out.append(dict(r, id=r.get("id") or learning_id(r["rule"]), stations=list(stations_of(r)),
                            brand=b, state=r.get("state", "active")))
    out.sort(key=lambda r: r.get("at", ""), reverse=True)
    return out


def _active_ids():
    ids = {r.get("id") or learning_id(r["rule"]) for r in load(None)}
    for f in (Path(paths.repo()) / "runs" / "learnings").glob("*.jsonl"):
        if f.name == CANDIDATES:
            continue
        b = None if f.stem == "_all" else f.stem
        ids |= {r.get("id") or learning_id(r["rule"]) for r in load(b)}
    return ids


def note(brand, stations, rule, kind="do", run="", file="", src="", by="", said="", said_rule=False, key=None,
         check=None, evidence=None, formats=None, one_off=False):
    """One candidate learning. Returns the row; `promoted` is True when this note put the rule in force."""
    stations = [s for s in (stations or ()) if s in STATIONS] or ["writing"]
    lid = learning_id(key or rule)
    row = {"id": lid, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "brand": brand,
           "stations": stations, "kind": kind if kind in ("do", "never") else "do", "rule": rule.strip(),
           "run": run, "file": file, "from": src, "by": by, "key": _norm(key or rule), "said_rule": bool(said_rule)}
    if check:
        row["check"] = check
    if formats:
        row["formats"] = list(formats)
    if one_off:
        row["one_off"] = True
    if evidence:
        row["evidence"] = {k: str(v)[:400] for k, v in evidence.items()}
    keep_quote(lid, said, run)
    if lid in _active_ids():                      # already in force: the note is a recurrence, nothing new to add
        row["promoted"] = False
        return row
    f = _cand_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    seen = [c for c in candidates() if c.get("id") == lid]
    if not any(c.get("run") == run and c.get("rule") == row["rule"] for c in seen):
        with f.open("a") as h:
            h.write(json.dumps(row, ensure_ascii=False) + "\n")
        seen.append(row)
    row["promoted"] = promote(lid)
    return row


def promote(lid):
    """A candidate goes in force when he stated it as a rule, or when RECUR distinct runs showed it."""
    seen = [c for c in candidates() if c.get("id") == lid]
    if not seen or lid in _active_ids():
        return False
    runs = {c.get("run") or c.get("at") for c in seen if not c.get("one_off")}
    if not (any(c.get("said_rule") for c in seen) or len(runs) >= RECUR):
        return False
    c = next((c for c in reversed(seen) if c.get("said_rule")), seen[-1])
    why = "stated as a rule" if any(x.get("said_rule") for x in seen) else "seen in %d runs" % len(runs)
    add(c.get("brand"), c["stations"][0], c.get("kind", "do"), c["rule"], why=why, by=c.get("by", ""),
        src=c.get("from", ""), stations=c["stations"], run=c.get("run", ""), file=c.get("file", ""),
        check=c.get("check"), lid=lid, formats=c.get("formats"))
    return True


def capture(brand, station, before, after, run="", file="", by="owner", said=""):
    """What the chain wrote against what was kept: one candidate per changed line. `before`/`after` are texts.
    The key is the change itself (words taken out, words put in), so the same fix in a second run puts it in force."""
    a = [x.strip() for x in str(before).splitlines() if x.strip()]
    b = [x.strip() for x in str(after).splitlines() if x.strip()]
    made = []
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        old, new = " / ".join(a[i1:i2]), " / ".join(b[j1:j2])
        wo, wn = set(_norm(old).split()), set(_norm(new).split())
        out_w, in_w = sorted(wo - wn), sorted(wn - wo)
        if not out_w and not in_w:
            continue                                 # punctuation or order only
        if op == "delete":
            rule = 'Cut lines like: "%s"' % old[:160]
        elif op == "insert":
            rule = 'Add what was missing: "%s"' % new[:160]
        else:
            rule = 'Write "%s", not "%s"' % (" ".join(in_w)[:120] or new[:120], " ".join(out_w)[:120] or old[:120])
        key = "change|%s|-%s|+%s" % (station, " ".join(out_w[:8]), " ".join(in_w[:8]))
        made.append(note(brand, [station], rule, "do", run=run, file=file, src="kept edit", by=by, said=said,
                         key=key, evidence={"chain": old, "kept": new}, one_off=bool(PRICE.search(old + " " + new))))
    return made


def harvest(queue=None, calls=None):
    """The decision layer's queue -> candidates: every call he overruled (his note kept in his node), and every take
    finding a run filed. Safe to run again: a candidate already filed for the same run is not filed twice."""
    if calls is None:
        q = Path(queue) if queue else Path(paths.repo()) / "runs" / "decisions" / "calls.jsonl"
        calls = []
        for x in (q.read_text().splitlines() if q.is_file() else []):
            try:
                calls.append(json.loads(x))
            except ValueError:
                continue
    made = []
    for c in calls:
        item = c.get("item") or {}
        el = str(item.get("element") or "").strip()
        if c.get("verdict") == "overrule":
            st = "video" if c.get("gate") in ("take", "elements", "clips", "pictures") else "writing"
            made.append(note(c.get("brand"), [st], "Never let this pass at the %s check: %s" % (c.get("gate"), el[:200]),
                             "never", run=c.get("run", ""), src="overruled call " + str(c.get("id")), by="owner",
                             said=c.get("note", ""), key="overrule|%s|%s" % (c.get("kind"), _norm(el)[:80])))
        elif c.get("gate") == "take" and el:
            made.append(note(c.get("brand"), ["video"], "Check every take's %s for this before it is kept: %s" % (item.get("status"), el[:200]),
                             "do", run=c.get("run", ""), src="take finding " + str(c.get("id")), by="run",
                             key="take|%s|%s" % (item.get("status"), _norm(el)[:80])))
    return made


def real_run(run_dir):
    """True for a run filed under the workspace's runs/ (builder card rule 1); a test's or sandbox's temp folder is
    not one, and is handed nothing, so its prompts stay exactly as its author wrote them."""
    try:
        Path(run_dir).resolve().relative_to((Path(paths.repo()) / "runs").resolve())
        return True
    except (ValueError, OSError):
        return False


def handed(run_dir, station, brand, chain=None, fmt=None):
    """The block a station's prompt carries, and the record of what it was handed (<run>/learnings-handed.json)."""
    rows = rules(brand, (station,), chain, fmt)
    text = "\n".join("- [%s] %s %s" % (r.get("id") or learning_id(r["rule"]), "DO:" if r["kind"] == "do" else "NEVER:",
                                       r["rule"]) for r in rows)
    if run_dir:
        f = Path(run_dir) / "learnings-handed.json"
        try:
            rec = json.loads(f.read_text()) if f.is_file() else {}
        except ValueError:
            rec = {}
        rec[station] = {"at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "ids": [r.get("id") or learning_id(r["rule"]) for r in rows]}
        try:
            f.write_text(json.dumps(rec, indent=1) + "\n")
        except OSError:
            pass
    if not rows:
        return ""
    return ("## WHAT EVERY EARLIER RUN TAUGHT (in force for this station; a NEVER never happens again, a DO always "
            "does; obey these over your own habits)\n" + text + "\n## END OF WHAT EARLIER RUNS TAUGHT\n\n")


def check_text(text, brand, stations, fmt=None, field="text"):
    """[(id, rule, why)] for every rule in force a draft breaks, by the rule's own `check` patterns. `field` picks the
    pattern set: "text" (never / must) for words, "request" (request_never / request_must) for an outgoing clip
    request. A format-scoped rule is checked only when the caller names that format."""
    bad = []
    for r in rules(brand, stations, None, fmt):
        if r.get("formats") and fmt not in r["formats"]:
            continue
        raw = r.get("check") or {}
        ck = raw if field == "text" else {k[len(field) + 1:]: v for k, v in raw.items() if k.startswith(field + "_")}
        for pat in ck.get("never") or []:
            m = re.search(pat, text or "", re.I | re.M)
            if m:
                bad.append((r.get("id") or learning_id(r["rule"]), r["rule"], 'has "%s"' % m.group(0)[:60]))
        for pat in ck.get("must") or []:
            if not re.search(pat, text or "", re.I | re.M):
                bad.append((r.get("id") or learning_id(r["rule"]), r["rule"], "is missing what it requires"))
    return bad


def findings(text, brand, stations, fmt=None, field="text"):
    """check_text as plain lines a station's repair loop can hand back to its writer."""
    return ["Breaks learning %s (%s): %s" % (i, why, rule)
            for i, rule, why in check_text(text, brand, stations, fmt, field)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--brand")
    a.add_argument("--chain", default="all")
    a.add_argument("--stage", choices=STAGES, required=True)
    a.add_argument("--kind", choices=("do", "never"), required=True)
    a.add_argument("--rule", required=True)
    a.add_argument("--why", default="")
    a.add_argument("--by", default="")
    a.add_argument("--from", dest="src", default="")
    li = sub.add_parser("list")
    li.add_argument("--brand")
    li.add_argument("--stage")
    r = sub.add_parser("retire")
    r.add_argument("--brand")
    r.add_argument("--n", type=int, required=True)
    r.add_argument("--why", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--brand")
    c.add_argument("--station", choices=STATIONS, required=True)
    c.add_argument("--run", default="")
    c.add_argument("--before", required=True, help="the file the chain wrote")
    c.add_argument("--after", required=True, help="the file as it was kept")
    c.add_argument("--said", default="")
    n = sub.add_parser("note")
    n.add_argument("--brand")
    n.add_argument("--station", choices=STATIONS, action="append", required=True)
    n.add_argument("--kind", choices=("do", "never"), default="do")
    n.add_argument("--rule", required=True)
    n.add_argument("--run", default="")
    n.add_argument("--file", default="")
    n.add_argument("--from", dest="src", default="")
    n.add_argument("--by", default="owner")
    n.add_argument("--said", default="", help="his words: kept in his own node only, never in the repo")
    n.add_argument("--rule-said", dest="said_rule", action="store_true", help="he stated it as a rule: in force now")
    n.add_argument("--never-pattern", action="append", default=[], help="a regex a draft must not contain")
    n.add_argument("--format", dest="formats", action="append", default=[], help="only this format (repeatable)")
    sub.add_parser("harvest")
    f = sub.add_parser("in-force")
    f.add_argument("--brand")
    f.add_argument("--json", action="store_true")
    k = sub.add_parser("check")
    k.add_argument("file")
    k.add_argument("--brand")
    k.add_argument("--station", choices=STATIONS, action="append", required=True)
    x = ap.parse_args()
    if x.cmd == "capture":
        made = capture(x.brand, x.station, Path(x.before).read_text(), Path(x.after).read_text(), run=x.run,
                       file=x.after, said=x.said)
        for m in made:
            print("%s %s %s" % (m["id"], "IN FORCE" if m.get("promoted") else "candidate", m["rule"]))
        return
    if x.cmd == "note":
        m = note(x.brand, x.station, x.rule, x.kind, run=x.run, file=x.file, src=x.src, by=x.by, said=x.said,
                 said_rule=x.said_rule, check={"never": x.never_pattern} if x.never_pattern else None,
                 formats=x.formats or None)
        print("%s %s %s" % (m["id"], "IN FORCE" if m.get("promoted") or m["id"] in _active_ids() else "candidate", m["rule"]))
        return
    if x.cmd == "harvest":
        made = harvest()
        print("%d candidate(s) read, %d now in force" % (len(made), sum(1 for m in made if m.get("promoted"))))
        return
    if x.cmd == "in-force":
        rows = in_force(x.brand)
        if x.json:
            print(json.dumps(rows, indent=1, ensure_ascii=False))
        for r in rows if not x.json else []:
            print("%s %s %-22s %s" % (r["id"], r.get("at", ""), ",".join(r["stations"]), r["rule"][:110]))
        return
    if x.cmd == "check":
        bad = findings(Path(x.file).read_text(), x.brand, x.station)
        print("\n".join(bad) or "PASS: breaks no learning in force")
        raise SystemExit(1 if bad else 0)
    if x.cmd == "add":
        print(json.dumps(add(x.brand, x.stage, x.kind, x.rule, x.why, x.by, x.src, x.chain), ensure_ascii=False))
    elif x.cmd == "list":
        for row in load(x.brand):
            if not x.stage or row["stage"] == x.stage:
                print("%3d  %-6s %-8s %-5s %s" % (row["n"], row.get("chain", "all"), row["stage"], row["kind"], row["rule"]))
    else:
        retire(x.brand, x.n, x.why)
        print("retired %d" % x.n)


if __name__ == "__main__":
    main()
