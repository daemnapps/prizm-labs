"""The free dry run — everything a request resolves to, and nothing spent.

It resolves and prints, per request: the purpose and the frame · the brand's
folder · the style, format and template named · the product, its real
photograph and what the brand says is true of it · the logo · the palette ·
the fonts · the references that would be attached · the PROMPT EXACTLY AS IT
WOULD BE SENT · the model it routes to and why · whether that model's key is
on this machine · what the gates would say · and where the files would land,
in `out` and on Drive.

**It starts no model, judges nothing, and writes no file** — not in `out`,
not under the repo-root `runs/`, not on Drive. Exit 1 when anything REQUIRED
is missing or a gate would hold; exit 0 otherwise.

Lifted in shape from `tools/image-production/static/tools/dryrun.py`, including
its OK / -- / MISSING report and its reason for existing: a dry run that
costs money is a dry run nobody runs.
"""
from pathlib import Path

from . import engine, filing, gates, judge, paths as P, providers, route as R


class Report:
    def __init__(self):
        self.missing = 0
        self.problems = []

    def ok(self, what, detail=""):
        print(f"    OK       {what:<16} {detail}")

    def note(self, what, detail=""):
        print(f"    --       {what:<16} {detail}")

    def bad(self, what, detail=""):
        self.missing += 1
        print(f"    MISSING  {what:<16} {detail}")

    def head(self, text):
        print(f"\n  {text}")


def run(req, library=None, purposes_map=None, table=None):
    """Returns (report, resolved) — the caller decides the exit code."""
    r = Report()
    try:
        req, ctx, prompt, prompt_path, model_id, entry, why = engine.resolve(
            req, library, purposes_map, table)
    except SystemExit as e:
        print(f"    MISSING  request          {e}")
        r.missing += 1
        return r, None

    t = table or R.table()
    purpose = ctx["purpose"]

    r.head(f"{ctx['brand']} · {purpose['id']} · {req['_aspect']} · "
           f"{req['_count']} picture(s)")
    r.ok("purpose", f"{purpose['name']} — {purpose['what']}")
    r.ok("brand", ctx["brand_root"])

    r.head("what it was asked for")
    r.ok("direction", " ".join(str(req["direction"]).split())[:160])

    r.head("elements")
    picked = ctx["elements"]["picked"]
    rows = ctx["elements"]["rows"]
    if not picked:
        r.note("style/format", "none named — the purpose's frame and the direction carry it")
    for field, value in picked.items():
        if field in rows:
            r.ok(field, f"`{value}` — {rows[field].get('name') or ''}")
        else:
            r.bad(field, f"`{value}` is not a row in the element library")
    for p in ctx["elements"]["problems"]:
        r.problems.append(f"elements: {p}")

    r.head("the brand's own facts")
    prod = ctx["product"]
    if prod["key"]:
        r.ok("product", f"{prod['title']} (`{prod['key']}`)")
        need = purpose.get("product_reference", "none")
        if prod["photo"] and prod["photo_on_machine"]:
            r.ok("product photo", f"{P.rel(prod['photo'])} — {prod['photo_note']}")
        elif prod["photo"]:
            (r.bad if need == "required" else r.note)(
                "product photo", f"{prod['photo']} — {prod['photo_note']}; not on this machine")
        else:
            (r.bad if need == "required" else r.note)("product photo", prod["photo_note"])
        if prod["facts"]:
            r.ok("product facts", prod["facts"][:150])
        else:
            r.note("product facts", prod["facts_note"] or "none on file")
    else:
        r.note("product", "none named — nothing of the product goes into the prompt")
    if ctx["logo"]:
        r.ok("logo", ", ".join(P.rel(x) for x in ctx["logo"]))
    else:
        r.note("logo", "none on file — no logo is drawn")
    if ctx["palette"]:
        r.ok("palette", f"{len(ctx['palette'])} colours from {', '.join(ctx['palette_from'])}")
    else:
        r.note("palette", "no colour written down in the brand's identity files")
    r.note("fonts", P.rel(ctx["fonts"]) if ctx["fonts"] else "no fonts.md on file")
    if ctx["references"]:
        r.ok("references", ", ".join(P.rel(x) for x in ctx["references"]))
    else:
        r.note("references", "none attached — this is a fresh render, not an edit")
    for m in ctx["_missing_objects"]:
        if m.fatal:
            r.bad(m.what, m.detail)

    r.head("the model")
    r.ok("routes to", f"{model_id} — {why}")
    r.ok("vendor", f"{entry['provider']} · {entry['vendor_model']}")
    size = R.size_for(entry, req["_gen_aspect"])
    r.note("frame asked as", size or f"aspectRatio {req['_gen_aspect']}")
    if req.get("_finish"):
        r.note("delivered as", f"{req['_aspect']} — the {req['_gen_aspect']} content taped down, "
                               "the strips above and below painted (finish_9x16)")
    kname = R.key_name(entry)
    if R.key_present(entry):
        r.ok("key", f"{kname} — on this machine (environment, else the Keychain)")
    else:
        r.bad("key", f"{kname} — not in the environment and not in the Keychain "
                     f"(service daemn-{kname}, account damon)")
    jentry = R.judge_entry(t)
    if R.key_present(jentry):
        r.ok("judge key", f"{jentry['key']} — on this machine")
    else:
        r.bad("judge key", f"{jentry['key']} — not on this machine; the judge could not run, "
                           f"and a judge that does not run HOLDS the picture")
    p = providers.plan(entry, prompt, [Path(x) for x in ctx["references"]], req["_gen_aspect"])
    r.note("request", f"{p['method']} {p['url']}")

    r.head("the prompt, exactly as it would be sent")
    print("    " + "\n    ".join(prompt.splitlines()))
    r.note("skeleton", P.rel(prompt_path))

    r.head("what the judge would ask")
    for i, test in enumerate(judge.tests_for(req, ctx), 1):
        print(f"    {i}. {test[:150]}")

    r.head("what the gates would say")
    pmap = purposes_map if purposes_map is not None else engine.purposes()
    ins = gates.input_problems(req, ctx, pmap, R.aspects(t))
    r.problems += [f"inputs: {p}" for p in ins]
    for name, probs in (("inputs", ins),
                        ("elements", ctx["elements"]["problems"])):
        if probs:
            for p in probs:
                r.bad(name, p)
        else:
            r.ok(name, "pass")
    r.note("media", "runs after the judge — a picture it fails is held from delivery")

    r.head("where it would land")
    stem = judge.slug(req.get("label") or req["purpose"])
    r.ok("out", f"{req['out']}/{stem}-01.png … ({req['_count']} of them), "
                f"plus prompt-as-sent.txt, elements.json, check.json, run.json")
    where, note = filing.drive_plan(ctx["brand"], filing.label_for(req))
    if where:
        r.ok("drive", where)
    else:
        r.note("drive", f"{note} — the pictures would still land in out/")

    print("\n  nothing was generated, judged, written or spent.")
    return r, {"request": req, "context": ctx, "prompt": prompt, "model": model_id}
