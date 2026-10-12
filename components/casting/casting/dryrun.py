"""The free dry run — everything a request resolves to, and nothing spent.

It resolves and prints: the role · whether the bank already covers it, and who
· every baseline candidate the owned footage offers and WHY each one · the
baseline it would pick · the PROMPTS EXACTLY AS THEY WOULD BE SENT, per
generating step · whether the generator's door and key are on this machine ·
what the judge would ask · what the gates would say · and where every file
would land, in the run folder, in the brand's cast folder and on Drive.

**It starts no model, makes no fal call, judges nothing, and writes no file
except image-production's listing cache under ~/.cache/daemn/asset-index** —
not in the run folder, not under `brands/`, not on Drive. Exit 1 when
anything REQUIRED is missing or a gate would hold; exit 0 otherwise.

Lifted in shape from
`tools/image-production/image_production/dryrun.py`, including its
OK / -- / MISSING report and its reason for existing: a dry run that costs
money is a dry run nobody runs.
"""
from . import engine as E
from . import filing, gates, judge, paths as P
from . import generate as G


class Report:
    def __init__(self):
        self.missing = 0
        self.problems = []

    def ok(self, what, detail=""):
        print("    OK       %-16s %s" % (what, detail))

    def note(self, what, detail=""):
        print("    --       %-16s %s" % (what, detail))

    def bad(self, what, detail=""):
        self.missing += 1
        print("    MISSING  %-16s %s" % (what, detail))

    def head(self, text):
        print("\n  %s" % text)


def _who(r, answer):
    r.head("who plays this role")
    bank = answer["bank"]
    r.ok("the bank", "%d banked — %s; read from %s"
         % (bank["people"],
            ", ".join("%s %s" % (v, k) for k, v in sorted(bank["by_record"].items()))
            or "nothing",
            ", ".join(bank["sources"]) or "no record on disk"))
    if answer["covered"]:
        p = answer["person"]
        r.ok("already cast", "%s (`%s`) in %s — %s"
             % (p.get("name") or p["id"], p["id"], p["where"], answer["why"]))
        c = answer["castable"]
        r.ok("castable", "image chain: %s · cinema line: %s"
             % ("yes" if c["image_chain"] else "no picture banked",
                "yes" if c["cinema"] else "no"))
        for w in c["why"]:
            r.note("still open", w)
        # Always shown, even when one person clearly wins: a near-tie between
        # two banked people is a casting decision, and hiding the runner-up is
        # how the wrong one gets used without anybody seeing the choice.
        for row in answer["candidates"][1:4]:
            r.note("also read", row["why"])
    else:
        r.note("gap", answer["gap"]["said"])
        for n in answer["gap"].get("near") or []:
            r.note("nearest", n)
        for o in answer["gap"].get("open_items") or []:
            r.note("on record", o[:150])
    for p in answer["problems"]:
        r.bad("registry", p)


def who(brand, role, start=None, banked=None):
    """The question on its own — free, and free of a build's requirements."""
    r = Report()
    try:
        answer = E.cast(brand, role, start, banked)
    except SystemExit as e:
        r.bad("request", str(e))
        return r, None
    r.head("%s · %s" % (brand, role))
    _who(r, answer)
    print("\n  nothing was generated, judged, written or spent.")
    return r, answer


def run(req, lib=None, reader=None, start=None, banked=None):
    """The whole build, resolved. Returns `(report, resolved)` — the caller
    decides the exit code."""
    r = Report()
    try:
        req, answer, prompts = E.resolve(req, lib, reader, start, banked)
    except SystemExit as e:
        r.bad("request", str(e))
        return r, None

    r.head("%s · %s · `%s` (%s)"
           % (req["brand"], req["role"], req.get("id") or "(no id)",
              req.get("kind") or "no kind declared"))
    _who(r, answer)

    r.head("the nine steps")
    for s in E.STEPS:
        detail = s["what"]
        if s["key"] == "detail" and not req.get("detail"):
            detail += " — SKIPPED: the request names no `detail`"
        print("    %d %-9s %-9s %s" % (s["n"], s["key"], s["kind"], detail))

    r.head("elements")
    el = req["_elements"]
    if not el["picked"]:
        r.note("style/format", "none named — the baseline's world carries the look")
    for field, value in el["picked"].items():
        if field in el["rows"]:
            r.ok(field, "`%s` — %s" % (value, el["rows"][field].get("name") or ""))
        else:
            r.bad(field, "`%s` is not a usable row in the element library" % value)
    for p in el["problems"]:
        r.problems.append("elements: %s" % p)

    r.head("the baseline — identity comes from an IMAGE, never a paragraph")
    base = req["_baseline"]
    for c in base["candidates"][:6]:
        r.note("candidate", "%s  [%s]" % (c["why"], c["source"]))
    for n in base["notes"]:
        r.note("search", n)
    if base["baseline"]:
        (r.ok if base["on_this_machine"] else r.bad)(
            "baseline", "%s — %s%s" % (P.rel(base["baseline"], start), base["why"],
                                       "" if base["on_this_machine"]
                                       else "  (NOT a file on this machine)"))
    else:
        r.bad("baseline", "nothing matched — a person picks the frame")

    r.head("the generator")
    for key in E.GENERATING:
        if key not in prompts:
            continue
        plan = G.plan(key, base["baseline"] if key == "master" else "(the master sheet)")
        r.ok("model", "%s — %s" % (key, plan["model"]))
    plan = G.plan("master", base["baseline"] or "")
    (r.ok if plan["client_on_this_machine"] else r.bad)(
        "door", "%s%s" % (plan["door"], "" if plan["client_on_this_machine"]
                          else "  (not on this machine)"))
    (r.ok if plan["key_on_this_machine"] else r.bad)(
        "key", "%s — %s" % (plan["key"],
                            "on this machine (environment, else the Keychain)"
                            if plan["key_on_this_machine"] else
                            "not in the environment and not in the Keychain "
                            "(service daemn-%s, account damon)" % plan["key"]))

    for key in E.GENERATING:
        if key not in prompts:
            continue
        r.head("step %s — the prompt, exactly as it would be sent (%s)"
               % (key, prompts[key]["skeleton"]))
        print("    " + "\n    ".join(prompts[key]["text"].splitlines()))
        r.head("step %s — what the judge would ask" % key)
        for i, t in enumerate(judge.tests_for(key, req), 1):
            print("    %d. %s" % (i, t[:150]))

    r.head("what the gates would say")
    ins = gates.input_problems(req, answer, build=True, start=start)
    r.problems += ["inputs: %s" % p for p in ins]
    for name, probs in (("inputs", ins), ("elements", el["problems"])):
        if probs:
            for p in probs:
                r.bad(name, p)
        else:
            r.ok(name, "pass")
    r.note("media", "runs after the judge — a sheet it fails is held, is never "
                    "filed into the brand's cast folder, and nothing later "
                    "references it")

    r.head("where it would land")
    label = filing.label_for(req)
    run_at = req.get("out") or str(filing.plan_run_dir(req["brand"], label, start))
    r.ok("the run", "%s/ — prompt-as-sent per step, run.json, check.json, "
                    "elements.json, register/, bible/" % P.rel(run_at, start))
    if req.get("id"):
        c = P.character(req["brand"], req["id"], start)
        r.ok("the character", "%s/ — master-sheet.png, boards/character-sheet.png%s"
             % (P.rel(c["root"], start),
                ", boards/detail.png" if req.get("detail") else ""))
        where, note = filing.drive_plan(req["brand"], req["id"])
        if where:
            r.ok("drive", where)
        else:
            r.note("drive", "%s — the sheets would still be on this machine" % note)
    r.ok("the registry", "PROPOSED only — register/proposed-row.json and "
                         "register/REGISTER.md in the run. A person registers it; "
                         "brands/ is read-only to machines this phase")

    print("\n  nothing was generated, judged, written or spent.")
    return r, {"request": req, "answer": answer, "prompts": prompts}
