#!/usr/bin/env python3
"""claimfix.py — every spoken and on-screen line of a brief held to the BRAND'S OWN
claim rules (each product file's "Claims" section: allowed / forbidden, plus its
known-issues note), fixed in place. Brand-agnostic; runs on every brief.

the owner, 2026-09-23 (Nova's "this tells those cells to stop" — flagged by the
product file as past appearance-only wording): "where are you sourcing these from?
… clean up anything else so I can just get to printing."

    python3 machine/claimfix.py <brief.md> --brand <brand> [--product <id>]

One model call (prompts/stage-0e-claims/, checks tier) with the rules and the lines.
Only the breaking words change; each fix is noted in the brief with the rule it broke.
"""
from __future__ import annotations
import argparse, datetime as dt, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(p for p in [HERE, *HERE.parents] if (p / "components").is_dir() and (p / "brands").is_dir())
PROMPTS = HERE.parent / "prompts" / "stage-0e-claims"
# loaded by file, never by putting this folder first on sys.path: this folder
# has a `platform.py`, and a caller that imports claimfix (the teardown's
# stage-5 hook) then got it in place of Python's own `platform` module — which
# broke the teardown's Drive step on 2026-09-23
import importlib.util as _ilu  # noqa: E402
_sp = _ilu.spec_from_file_location("vm_slotfill", HERE / "slotfill.py")
SL = _ilu.module_from_spec(_sp); _sp.loader.exec_module(SL)  # the same brief block reader


def claim_rules(brand: str, product: str | None = None) -> str:
    b = WS / "brands" / brand / "products"
    files = [b / product / "product.md"] if product else sorted(b.glob("*/product.md"))
    out = []
    for f in files:
        if not f.is_file():
            continue
        t = f.read_text()
        head = "\n".join(l for l in t.splitlines()[:15] if re.search(r"known-issues|claim", l, re.I))
        m = re.search(r"^## Claims.*?(?=^## |\Z)", t, flags=re.S | re.M)
        if m or head:
            out.append(f"### {f.relative_to(WS)}\n{head}\n\n{m.group(0) if m else ''}")
    return "\n\n".join(out) or "(no claim rules on file)"


def lines_of(doc: dict) -> list[dict]:
    rows = []
    for sc in doc.get("scenes") or []:
        if sc.get("voice"):
            rows.append({"id": f"{sc['id']}.voice", "scene": sc["id"], "path": ("voice", None), "text": sc["voice"]})
        for k in ("card", "screen", "endcard"):
            box = sc.get(k)
            if isinstance(box, dict):
                for f in ("lines", "offer_lines"):
                    for i, t in enumerate(box.get(f) or []):
                        if str(t).strip():
                            rows.append({"id": f"{sc['id']}.{k}.{f}.{i}", "scene": sc["id"], "path": (f"{k}.{f}", i), "text": t})
    return rows


def fix(brief: Path, brand: str, product: str | None = None, call=None) -> list[dict]:
    text = brief.read_text()
    m, doc = SL._block(text)
    if doc is None:
        return []
    rows = lines_of(doc)
    sys.path.insert(0, str(WS / "components" / "run-kit"))
    from run_kit import prompts as P
    sent = P.fill(Path(P.latest(PROMPTS, "stage0e-claims")).read_text(),
                  {"claim_rules": claim_rules(brand, product), "lines": "\n".join(f"- {r['id']}: \"{r['text']}\"" for r in rows)})
    if call is None:
        from run_kit import model as M
        mdl, _ = M.pick("checks", len(sent))
        call = lambda p: M.call(p, mdl, label="claims")
    reply = call(sent)
    d = json.loads(reply[reply.index("{"): reply.rindex("}") + 1])
    by = {r["id"]: r for r in rows}
    done = []
    for f in d.get("fixes") or []:
        r = by.get(f.get("id"))
        if not r or not str(f.get("now") or "").strip():
            continue
        sc = next(s for s in doc["scenes"] if s["id"] == r["scene"])
        key, i = r["path"]
        obj = sc
        if "." in key:
            a, key = key.split(".", 1)
            obj = sc[a]
        if i is None:
            obj[key] = f["now"].strip()
        else:
            obj[key][i] = f["now"].strip()
        text = text.replace(r["text"], f["now"].strip())
        done.append({"scene": r["scene"], "was": r["text"], "now": f["now"].strip(), "rule": f.get("rule", "")})
    if done:
        m2, _ = SL._block(text)
        text = text[:m2.start(1)] + json.dumps(doc, indent=1, ensure_ascii=False) + text[m2.end(1):]
        text += ("\n\n## Claims held to the brand's rules (automatic, " + dt.date.today().isoformat() + ")\n\n"
                 + "\n".join(f"- {c['scene']}: now \"{c['now']}\" — rule: {c['rule']}" for c in done) + "\n")
        brief.write_text(text)
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief"); ap.add_argument("--brand", required=True); ap.add_argument("--product")
    a = ap.parse_args(argv)
    for c in fix(Path(a.brief), a.brand, a.product):
        print(f"{c['scene']}: {c['now']}\n    rule: {c['rule']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
