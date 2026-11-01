"""The question in, the answer out — and the nine steps when the answer is a gap.

This is the whole of the component's API.

    import casting
    casting.cast(brand="…", role="…")          who plays this role?
    casting.build({...})                       the nine steps, for a gap
    casting.dry_run({...})                     the same, spending nothing

**THE NINE STEPS, as declared steps.** Steps 4–6 generate; everything else is
files.

    1 GAP       a brief names a role the bank has no one for
    2 SEARCH    the owned footage, for that archetype
    3 BASELINE  pick one frame — a real shot of a real room
    4 MASTER    reference in, "a different one" out       → master-sheet.png
    5 ANCHOR    the 3x3 sheet off the master              → boards/character-sheet.png
    6 DETAIL    the continuity board the format leans on  → boards/<detail>.png
    7 BIBLE     character.md — who they are, and what is load-bearing
    8 REGISTER  the proposed row, for a person to register
    9 MIRROR    Drive: the sheets and a small copy

**The rule the whole chain turns on: identity comes from an IMAGE, never from
a paragraph.** A character written as prose is a different person every roll,
which is the exact failure the cast bank exists to prevent. So step 3 is not
optional and cannot be replaced by a better description.

The request contract is declared in this folder's CLAUDE.md and enforced here;
a field nothing on the list names is REFUSED rather than ignored, because a
silently dropped field is a caller that thinks it asked for something.
"""
import shutil
from pathlib import Path

from . import bank as B
from . import filing, gates, judge, paths as P, prompting, registration, search
from . import generate as G

STEPS = [
    {"key": "gap", "n": 1, "name": "Gap", "kind": "files",
     "what": "a brief names a role the bank has no one for"},
    {"key": "search", "n": 2, "name": "Search", "kind": "files",
     "what": "the owned footage, for that archetype"},
    {"key": "baseline", "n": 3, "name": "Baseline", "kind": "files",
     "what": "one frame — a real shot of a real room"},
    {"key": "master", "n": 4, "name": "Master sheet", "kind": "generate",
     "what": "reference in, a DIFFERENT person out", "reference": "baseline"},
    {"key": "anchor", "n": 5, "name": "Anchor", "kind": "generate",
     "what": "the 3x3 sheet off the master — what every later shot references",
     "reference": "master"},
    {"key": "detail", "n": 6, "name": "Detail board", "kind": "generate",
     "what": "the continuity board the format leans on", "reference": "master",
     "when": "the request names a `detail`"},
    {"key": "bible", "n": 7, "name": "Bible", "kind": "files",
     "what": "character.md — who they are, and what is load-bearing"},
    {"key": "register", "n": 8, "name": "Register", "kind": "files",
     "what": "the proposed row — a person registers it, never this"},
    {"key": "mirror", "n": 9, "name": "Mirror", "kind": "files",
     "what": "Drive: the sheets, and a small copy of the master"},
]
GENERATING = [s["key"] for s in STEPS if s["kind"] == "generate"]

REQUIRED = ("brand", "role")
BUILD_REQUIRED = ("id", "kind", "who", "wardrobe", "world", "noun")
OPTIONAL = ("id", "kind", "who", "wardrobe", "world", "noun", "detail", "baseline",
            "like", "collection", "name", "out", "label", "style", "format",
            "lane", "fronts", "problem", "reads", "hair", "build", "face",
            "setting", "register", "age", "note", "checks", "rules")
FIELDS = set(REQUIRED) | set(OPTIONAL)


class BadRequest(SystemExit):
    pass


def _check_fields(req):
    unknown = sorted(set(req) - FIELDS - set(k for k in req if k.startswith("_")))
    if unknown:
        raise BadRequest(
            "the request carries fields this component does not take: %s — the "
            "contract is: %s" % (", ".join(unknown), ", ".join(sorted(FIELDS))))
    missing = [f for f in REQUIRED if not req.get(f)]
    if missing:
        raise BadRequest("the request is missing: %s" % ", ".join(missing))


# ------------------------------------------------------------- the question

def cast(brand=None, role=None, start=None, banked=None, **rest):
    """**The one call.** Who plays this role — the person already banked, or
    the gap. A role the bank covers NEVER gets a new face."""
    if rest:
        raise BadRequest("cast() takes brand and role: got also %s"
                         % ", ".join(sorted(rest)))
    P.need_brand(brand, "the cast bank", start)
    return B.who_plays(brand, role, start, banked)


# ------------------------------------------------------------- the nine steps

def resolve(req, lib=None, reader=None, start=None, banked=None):
    """Everything a request means, worked out without spending anything: the
    bank's answer, the elements, the baseline, and each generating step's
    prompt exactly as it would be sent."""
    _check_fields(req)
    req = dict(req)
    answer = cast(req["brand"], req["role"], start, banked)
    req["_answer"] = answer
    req["_elements"] = gates.resolve_elements(req, lib)
    req["_baseline"] = search.choose(
        req["brand"], req.get("like") or req["role"], req.get("baseline"),
        req.get("collection"), reader=reader, start=start)

    prompts = {}
    for key in GENERATING:
        if key == "detail" and not req.get("detail"):
            continue
        text, path = prompting.render(key, req)
        prompts[key] = {"text": text, "skeleton": P.rel(path, start),
                        "sha256_12": prompting.sha(path)}
    req["_prompts"] = prompts
    return req, answer, prompts


def build(req, lib=None, reader=None, runner=None, judge_caller=None,
          mirror=True, mode="hold", start=None, banked=None, echo=print):
    """The nine steps, run. Writes under the run folder, the brand's cast
    folder and the Drive mirror — nowhere else, and never into a registry."""
    req, answer, prompts = resolve(req, lib, reader, start, banked)
    out = filing.out_dir(req, start)

    # Every one of BUILD_REQUIRED is named, one by one, by the inputs gate —
    # so a caller is told all of what is missing at once, not the first thing.
    gates.inputs_gate(req, answer, out, build=True, mode=mode, start=start)
    gates.elements_gate(req, out, mode)

    steps, sheets, made, killed = [], {}, {}, []
    steps.append({"key": "gap", "status": "done",
                  "what": "the bank has no one for `%s`" % req["role"],
                  "bank": answer["bank"]})
    cand = req["_baseline"]["candidates"]
    steps.append({"key": "search", "status": "done",
                  "what": "%d baseline candidate(s)" % len(cand),
                  "notes": req["_baseline"]["notes"]})
    steps.append({"key": "baseline", "status": "done",
                  "what": P.rel(req["_baseline"]["baseline"], start),
                  "why": req["_baseline"]["why"]})

    gen_dir = Path(out) / "generated"
    reference = {"baseline": req["_baseline"]["baseline"]}
    for key in GENERATING:
        step = next(s for s in STEPS if s["key"] == key)
        if key not in prompts:
            steps.append({"key": key, "status": "skipped",
                          "why": "the request names no `detail`, and the board is "
                                 "whatever the format leans on — never a default"})
            continue
        ref = reference.get(step["reference"])
        if not ref:
            steps.append({"key": key, "status": "skipped",
                          "why": "`%s` was held or failed, and nothing is ever "
                                 "derived from a derivative" % step["reference"]})
            continue
        (Path(out) / ("%s--prompt-as-sent.txt" % key)).write_text(
            prompts[key]["text"] + "\n")
        r = G.generate(key, prompts[key]["text"], ref, gen_dir, runner=runner, echo=echo)
        if not r.get("file"):
            steps.append({"key": key, "status": "failed", "why": r.get("error")})
            sheets[key] = {"verdict": "failed", "fails": [r.get("error")]}
            killed.append((key, [r.get("error")]))
            continue
        v = judge.verdict(key, r["file"], req, judge_caller)
        sheets[key] = {"model": r["model"], "seconds": r.get("seconds"),
                       "verdict": v["verdict"], "fails": v["fails"],
                       "judge_model": v["judge_model"],
                       "checks_run": len(v["checks_run"])}
        if v["verdict"] == "pass":
            keep = gen_dir / ("%s.png" % key)
            gen_dir.mkdir(parents=True, exist_ok=True)
            if str(r["file"]) != str(keep):
                shutil.copy2(r["file"], keep)
            made[key] = str(keep)
            reference[key] = str(keep)
            steps.append({"key": key, "status": "done", "file": str(keep)})
        else:
            rej = Path(out) / "held"
            rej.mkdir(parents=True, exist_ok=True)
            shutil.copy2(r["file"], rej / ("%s.png" % key))
            (rej / ("%s-why.md" % key)).write_text(
                judge.why_md(key, v["fails"], v.get("raw")))
            killed.append((key, v["fails"]))
            steps.append({"key": key, "status": "held", "why": v["fails"]})

    gates.media_gate(out, killed)

    filed = filing.file_character(req["brand"], req["id"], made, start) if made else {}
    steps.append({"key": "bible", "status": "drafted",
                  "what": "a draft for a person to finish — never written into "
                          "the brand's folder by this component"})

    prop = registration.write(out, req, req["_baseline"], answer, filed, start)
    steps.append({"key": "register", "status": "proposed",
                  "what": "row for `%s`, list `people`" % prop["file"],
                  "path": prop["path"], "written": prop["written"]})

    drive = {"copied": [], "note": None}
    if mirror and filed:
        copied, note = filing.mirror(req["brand"], req["id"], filed)
        drive = {"copied": copied, "note": note}
        if note:
            echo("  %s" % note)
        steps.append({"key": "mirror", "status": "done" if copied else "skipped",
                      "what": "%d file(s)" % len(copied), "why": note})
    else:
        steps.append({"key": "mirror", "status": "skipped",
                      "why": "nothing was filed" if not filed else "mirror off"})

    held = gates.held(out)
    filing.record(out, req, answer, steps, prompts, sheets, filed, drive,
                  {"file": prop["file"], "path": prop["path"], "row": prop["row"]},
                  held, start)

    return {"out": str(out), "brand": req["brand"], "role": req["role"],
            "id": req["id"], "kind": req["kind"],
            "baseline": req["_baseline"]["baseline"],
            "steps": steps, "prompts": prompts, "sheets": sheets,
            "filed": filed, "drive": drive,
            "register": prop, "held": held,
            "still_open": prop["still_open"],
            "check": gates.state(out)}
