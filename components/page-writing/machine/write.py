#!/usr/bin/env python3
"""Page writing: the teardown's structure, filled with OUR brand — words from raw language-bank rows (cited by row
ID), offer and guarantee word for word from the offer file, facts from the product file, angle and voice from the
brand files — for the target topic. The writer never sees the source page, only its stripped structure.

Then the identity check: the deterministic test (page-teardown/machine/identity.py: the source's identity items,
names, and any 8-word run shared with the source) plus a model read for anything reworded or hinted. A page that
fails gets one fix pass and is checked again. The bank check: every cited row ID is a real row; every quote is its
row word for word.

    python3 write.py --brand <brand> --label <label> --avatar <avatar> --product <product file> \
        --offer <offer file> --next-url <url> --format "<format>" --topic "<topic>" [--target <brief.json>] \
        [--terms word word ...] [--sub <sub-avatar>] [--demographic m/25-34/black] [--resume]

Every writing step is handed who the page is for and what it must say (creative-strategist who.py) with the doctrine's
desire and belief slices; the same decisions are kept in run.json as `aim`.

Reads the run folder page-teardown wrote; writes page.json (the final page), write*/check*/fix* stages,
identity-result.json, bank-check.json.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TD = HERE.parents[1] / "page-teardown" / "machine"
sys.path.insert(0, str(TD))
import chain_io as C  # noqa: E402
import identity as I  # noqa: E402

sys.path.append(str(C.WS / "components" / "language-layer"))
from language_layer import engine as LANG  # noqa: E402

PROMPTS = HERE.parent / "prompts"
RETIRED = {"dropped", "inactive", "retired", "burned"}


def body_problems(brand, product, text):
    """Lines that use the product on a part of the body it is ruled out for (components/naming/body.py)."""
    p = str(C.WS / "components" / "naming")
    if p not in sys.path:
        sys.path.append(p)
    import body
    return body.problems(brand, product, text)


def who_aim(a):
    """(who the page is for + the doctrine it argues by, the same decisions as data). A named sub-avatar that does not
    exist stops the run; nothing else here ever does: an avatar with no profile is no block."""
    p = str(C.WS / "components" / "creative-strategist" / "machine")
    if p not in sys.path:
        sys.path.append(p)
    try:
        import who as W
        W.resolve(a.brand, a.avatar, a.sub)
        if not (W.avatar_dir(a.brand, a.avatar) / "profile.md").is_file():
            return "", None
        slices = [C.read_ws(f"components/marketing-doctrine/slices/{s}.md") for s in ("desire", "belief")]
        return ("\n\n".join([W.block(a.brand, a.avatar, a.sub, a.demographic, {"product": a.product})] + slices
                            + ["(The short ids above are for reading. `rows` cites only the ids under CUSTOMER LANGUAGE.)\n"]),
                W.stamp(a.brand, a.avatar, a.sub, a.demographic))
    except Exception as e:                       # SystemExit (a named sub that is not there) passes through
        print(f"  ! who it is for: not read ({type(e).__name__}: {str(e)[:120]})")
        return "", None


def target_text(a):
    lines = [f"Topic: {a.topic}"]
    if a.target:
        t = json.loads(Path(a.target).expanduser().read_text())
        s = t.get("searches") or []
        if s:
            lines.append("What people search (monthly searches):")
            lines += [f"- {x.get('search')} ({x.get('monthly_searches')})" for x in s[:20]]
        q = t.get("questions_to_answer") or {}
        qs = (q.get("people_also_ask") or []) + (q.get("from_top_pages_verbatim") or []) if isinstance(q, dict) else q
        if qs:
            lines.append("Questions searchers ask (answer the ones our files can answer):")
            lines += [f"- {x}" for x in qs[:15]]
    return "\n".join(lines)


def pick_rows(a, brief_ids):
    rows = [r for r in LANG.load(a.brand, a.avatar) if (r.get("status") or "active") not in RETIRED and r.get("id")]
    by_id = {r["id"]: r for r in rows}
    terms = [t.lower() for t in a.terms]
    def score(r):
        txt = (r.get("text") or "").lower()
        hit = sum(1 for t in terms if t in txt)
        n = len(txt.split())
        return (hit, 1 if 6 <= n <= 60 else 0, -abs(n - 20))
    chosen = [by_id[i] for i in brief_ids if i in by_id]
    seen = {r["id"] for r in chosen}
    pool = sorted((r for r in rows if r["id"] not in seen and score(r)[0] > 0), key=score, reverse=True)
    # a spread of kinds, not 150 rows of one: round-robin across the row's use
    by_use = {}
    for r in pool:
        u = r.get("use") or "untagged"; u = u[0] if isinstance(u, list) and u else (u if isinstance(u, str) else "untagged"); by_use.setdefault(u, []).append(r)
    while len(chosen) < a.rows and any(by_use.values()):
        for k in list(by_use):
            if by_use[k]:
                chosen.append(by_use[k].pop(0))
                if len(chosen) >= a.rows:
                    break
    return chosen, by_id


def page_text(page):
    return json.dumps(page, ensure_ascii=False)


def visible_text(page):
    out = [page.get("title", ""), page.get("meta_description", "")]
    for s in page.get("sections", []):
        for b in s.get("blocks", []):
            out += [b.get("text") or ""] + list(b.get("list") or [])
            for it in b.get("items") or []:
                out += [it.get("title", ""), it.get("text", "")]
            for f in b.get("faq") or []:
                out += [f.get("q", ""), f.get("a", "")]
    return "\n".join(x for x in out if x)


def bank_check(page, by_id):
    bad, cited, excerpts = [], set(), []
    for s in page.get("sections", []):
        for b in s.get("blocks", []):
            ids = list(b.get("rows") or [])
            for it in (b.get("items") or []) + (b.get("faq") or []):
                ids += it.get("rows") or []
            for i in ids:
                cited.add(i)
                if i not in by_id:
                    bad.append({"section": s.get("n"), "test": "bank", "kind": "bank", "problem": f"row {i} is not in the bank"})
            if b.get("type") == "quote":
                r = by_id.get((b.get("rows") or [None])[0])
                q, rt = I.norm(b.get("text", "")), I.norm((r or {}).get("text", ""))
                if not r or not q:
                    bad.append({"section": s.get("n"), "test": "bank", "kind": "bank",
                                "problem": "a quote with no bank row behind it", "text": b.get("text")})
                elif q != rt and not (q in rt and len(q.split()) >= 8):
                    bad.append({"section": s.get("n"), "test": "bank", "kind": "bank",
                                "problem": "a quote that is not its row word for word", "text": b.get("text")})
                elif q != rt:
                    excerpts.append({"section": s.get("n"), "row": r["id"], "text": b.get("text")})
    return {"pass": not bad, "rows_cited": len(cited), "problems": bad, "excerpts": excerpts}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True); ap.add_argument("--label", required=True)
    ap.add_argument("--avatar", required=True); ap.add_argument("--product", required=True)
    ap.add_argument("--offer", required=True); ap.add_argument("--next-url", required=True)
    ap.add_argument("--format", required=True); ap.add_argument("--topic", required=True)
    ap.add_argument("--target"); ap.add_argument("--terms", nargs="*", default=[])
    ap.add_argument("--rows", type=int, default=160)
    ap.add_argument("--sub", help="the sub-avatar the page speaks to (id or file name)")
    ap.add_argument("--demographic", help="e.g. m/25-34/black")
    ap.add_argument("--resume", action="store_true")
    import importlib.util as _u, pathlib as _pl
    _s = _u.spec_from_file_location("profile_arg", next(q for q in _pl.Path(__file__).resolve().parents if q.name == "components") / "naming" / "profile_arg.py")
    _PA = _u.module_from_spec(_s); _s.loader.exec_module(_PA)                                   # --profile <avatar>[_<sub>][_<demographic>] (naming/PEOPLE.md)
    a = ap.parse_args(_PA.expand(argv, has=("avatar", "sub", "demographic")))
    run = C.Run(a.brand, a.label)
    structure = json.loads((run.dir / "structure.json").read_text())
    ident = json.loads((run.dir / "identity-all.json").read_text())["items"]
    source = (run.dir / "source" / "page.txt").read_text()

    brief_ids = []
    if a.target:
        t = json.loads(Path(a.target).expanduser().read_text())
        for sec in t.get("section_order") or []:
            brief_ids += [x.get("row_id") for x in sec.get("customer_lines") or [] if x.get("row_id")]
    rows, by_id = pick_rows(a, brief_ids)
    lang = LANG.render(rows, header=f"{len(rows)} rows · avatar {a.avatar} · picked for: {', '.join(a.terms)}")
    who_block, aim = who_aim(a)
    bi = f"brands/{a.brand}/brand-identity"
    fields = dict(
        structure=json.dumps(structure, indent=1, ensure_ascii=False), brand=a.brand,
        position=C.read_ws(f"{bi}/position.md"), story=C.read_ws(f"{bi}/story.md"),
        voice=C.read_ws(f"brands/{a.brand}/core-avatars/{a.avatar}/language/rules.md"),
        compliance=C.read_ws(f"{bi}/compliance.json"), product=C.read_ws(a.product), offer=C.read_ws(a.offer),
        avatar=who_block + C.read_ws(f"brands/{a.brand}/core-avatars/{a.avatar}/profile.md"), language=lang,
        target=target_text(a), target_format=a.format, next_url=a.next_url)
    if aim:
        import who as W
        W.attach(run.dir, a.brand, a.avatar, a.sub, a.demographic, {"product": a.product})
    run.save(avatar=a.avatar, aim=aim, product=a.product, offer=a.offer, next_url=a.next_url, topic=a.topic,
             target_format=a.format, rows_offered=[r["id"] for r in rows])
    page = run.stage("write", PROMPTS, fields, tier="designs", resume=a.resume, order=3,
                     component="page-writing", title="Writing · our page from the structure")

    allow = [a.brand] + a.terms
    for rnd in (1, 2, 3):
        det = I.check(visible_text(page), source, ident, allow=allow)
        mod = run.stage(f"check@{rnd}", PROMPTS, dict(identity=json.dumps(ident, ensure_ascii=False),
                                                      page=page_text(page)),
                        tier="checks", resume=a.resume, order=3 + rnd * 2 - 1, component="page-writing",
                        title=f"Identity check · round {rnd}")
        bc = bank_check(page, by_id)
        survivors = ([dict(h, kind=f"identity · {h.get('kind')}") for h in det["hits"]]
                     + [dict(x, test="model", kind="identity · model read") for x in (mod.get("survivors") or [])]
                     + bc["problems"] + [{"kind": "body", "problem": x} for x in body_problems(a.brand, a.product, page_text(page))])
        (run.dir / f"identity-result-{rnd}.json").write_text(json.dumps(
            {"deterministic": det, "model": mod, "bank": bc, "pass": not survivors}, indent=1, ensure_ascii=False))
        print(f"  check round {rnd}: {'PASS' if not survivors else str(len(survivors)) + ' to fix'}")
        if not survivors or rnd == 3:
            break
        page = run.stage(f"fix@{rnd}", PROMPTS, dict(survivors=json.dumps(survivors, indent=1, ensure_ascii=False),
                                                    page=json.dumps(page, indent=1, ensure_ascii=False),
                                                    language=who_block + lang),
                         tier="designs", resume=a.resume, order=3 + rnd * 2, component="page-writing",
                         title=f"Fix · round {rnd}")
    idn = [x for x in survivors if x.get("test") != "bank"]
    result = {"pass": not idn, "rounds": rnd, "survivors": idn}
    (run.dir / "identity-result.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    (run.dir / "bank-check.json").write_text(json.dumps(bc, indent=1, ensure_ascii=False))
    (run.dir / "page.json").write_text(json.dumps(page, indent=1, ensure_ascii=False))
    run.save(identity_pass=result["pass"], bank_pass=bc["pass"])
    print(f"writing done: identity {'PASS' if result['pass'] else 'FAIL'} · bank {'PASS' if bc['pass'] else 'FAIL'} "
          f"({bc['rows_cited']} rows cited)")


if __name__ == "__main__":
    try:
        main()
    except C.UsageLimit as e:
        sys.exit(f"STOPPED — {e}\n  run the same command with --resume once usage is back")
