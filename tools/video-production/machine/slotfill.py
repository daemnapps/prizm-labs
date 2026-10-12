#!/usr/bin/env python3
"""slotfill.py — every hole a brief leaves in a spoken or on-screen line is filled
from the brand's OWN files, or cut cleanly. Brand-agnostic; runs on every brief.

the owner, 2026-09-23 (Nova's S5 left "[SLOT: how much per use …]" in a line June
would have read aloud; the answer was in the product file): "that's what you should
use anyways … this is why all of these should be an agnostic workflow and set up."

    python3 machine/slotfill.py <brief.md> --brand <brand> [--product <id>] [--dry-run]

1. Finds every `[SLOT: …]` / `[UNFILLED…]` inside a scene's `voice`, `lyrics` or a
   card/screen/endcard's lines in the brief's machine block.
2. One model call (prompts/stage-0d-slot-fill/, checks tier) with the brand's
   product file(s), offer bank and position — and nothing else.
3. A fill counts only if its `receipt` is really in that file (whitespace-insensitive);
   otherwise it is treated as not found and the line is CUT cleanly instead.
4. Applied to the brief (block + the readable text), with a note listing every fill
   and cut with its receipt. Production refuses any hole still left before the voice.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(p for p in [HERE, *HERE.parents] if (p / "components").is_dir() and (p / "brands").is_dir())
PROMPTS = HERE.parent / "prompts" / "stage-0d-slot-fill"
HOLE = re.compile(r"\[(?:SLOT|UNFILLED)[^\]]*\]", re.I)
BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


RESEARCH_FILES = ("facts-found.md", "failed-solutions.md")


def proposals_dir(brand: str) -> Path:
    """Where a fill's research lands: a proposal under runs/, never brands/ (K2 (brands write wall),
    SI-97 (brand research proposals)).
    A person commits accepted rows into brands/<brand>/intake/research/."""
    return WS / "runs" / "video-production" / brand / "research-proposals"


def brand_files(brand: str, product: str | None = None) -> dict[str, str]:
    """{name: text} — the product file(s), the offer bank, the position. Only these."""
    b = WS / "brands" / brand
    out = {}
    prods = [b / "products" / product / "product.md"] if product else sorted((b / "products").glob("*/product.md"))
    for p in prods:
        if p.is_file():
            out[str(p.relative_to(WS))] = p.read_text()
    for rel in ("products/offer-bank.md", "brand-identity/position.md", "intake/research/facts-found.md", "intake/research/failed-solutions.md"):
        p = b / rel
        if p.is_file():
            out[str(p.relative_to(WS))] = p.read_text()
    for name in RESEARCH_FILES:  # open proposals a person has not committed yet, SI-97 (brand research proposals)
        p = proposals_dir(brand) / name
        if p.is_file():
            out[str(p.relative_to(WS))] = p.read_text()
    return out


def _block(text: str):
    for m in BLOCK.finditer(text):
        try:
            d = json.loads(m.group(1))
        except Exception:
            continue
        if isinstance(d, dict) and "scenes" in d:
            return m, d
    return None, None


def holes_of(doc: dict) -> list[dict]:
    """Every hole in a spoken or on-screen line: {id, scene, field, index, line, hole}."""
    out = []
    for sc in doc.get("scenes") or []:
        fields = [("voice", None), ("lyrics", "list")]
        for k in ("card", "screen", "endcard"):
            if isinstance(sc.get(k), dict):
                fields += [(f"{k}.lines", "list"), (f"{k}.offer_lines", "list")]
        fields += [("lines", "list")]
        for f, kind in fields:
            obj, key = sc, f
            if "." in f:
                a, key = f.split(".", 1)
                obj = sc.get(a) or {}
            val = obj.get(key)
            items = list(enumerate(val)) if isinstance(val, list) else ([(None, val)] if isinstance(val, str) else [])
            for i, line in items:
                for h in HOLE.findall(str(line or "")):
                    out.append({"id": f"H{len(out) + 1}", "scene": sc.get("id"), "field": f, "index": i, "line": line, "hole": h})
    return out


def _hole_text(h: dict, doc: dict) -> str:
    """The hole with enough of its scene around it to answer it right: the scene's
    section and job, what it shows, what it lands on, the words said before and
    after it, and the other lines on the same card."""
    scs = doc.get("scenes") or []
    i = next((n for n, s in enumerate(scs) if s.get("id") == h["scene"]), 0)
    sc = scs[i]
    near = lambda k: (scs[k].get("voice") or "") if 0 <= k < len(scs) else ""
    box = next((sc.get(k) for k in ("card", "screen", "endcard") if isinstance(sc.get(k), dict)), {}) or {}
    return (f"- {h['id']} · scene {h['scene']} · {sc.get('kind') or ''} · section `{sc.get('section')}` · field {h['field']}\n"
            f"  the hole {h['hole']} in: \"{h['line']}\"\n"
            + (f"  the other lines on this {next((k for k in ('card','screen','endcard') if isinstance(sc.get(k), dict)), '')}: {json.dumps(box.get('lines') or box.get('offer_lines'), ensure_ascii=False)} · surface: {box.get('surface', '')} · lands on the words: \"{box.get('lands_on', '')}\"\n" if box else "")
            + f"  what the scene is: {sc.get('happens') or sc.get('outcome') or ''}\n"
            f"  said just before: \"{near(i - 1)}\"\n  said in this scene: \"{sc.get('voice') or ''}\"\n  said just after: \"{near(i + 1)}\"")


def research_call(prompt: str, timeout: int = 900) -> str:
    """A research call with tools: read the brand folder, search the web. Runs in
    the workspace; the reply is the JSON the prompt asks for.

    THE SESSION HAND (2026-10-05): when DAEMN_HAND_DIR is set — the CLI login is
    down and a Claude session is writing the stages (video-teardown run.py
    `claude()`) — the research goes the same way: the prompt is left there as
    slots-<hash>.prompt.md and the run stops; the session researches it, writes
    slots-<hash>.md beside it, and the run is resumed. Without this the rewrite
    held on the expired login while every other stage was writable (Brand B's device
    rebuild, the owner's OK)."""
    import hashlib, os
    hand = os.environ.get("DAEMN_HAND_DIR")
    if hand:
        hd = Path(hand); hd.mkdir(parents=True, exist_ok=True)
        done = hd / f"slots-{hashlib.sha1(prompt.encode()).hexdigest()[:8]}.md"
        if not done.exists():
            done.with_suffix(".prompt.md").write_text(prompt)
            raise RuntimeError(f"waiting for the session hand: {done.with_suffix('.prompt.md')}")
        return done.read_text()
    import subprocess
    r = subprocess.run(["claude", "-p", "--model", "claude-sonnet-5", "--output-format", "text",
                        "--allowedTools", "Read", "Grep", "Glob", "WebSearch", "WebFetch"],
                       input=prompt, capture_output=True, text=True, cwd=str(WS), timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-400:])
    return r.stdout


def fill(brief: Path, brand: str, product: str | None = None, call=None, dry_run: bool = False) -> dict:
    text = brief.read_text()
    m, doc = _block(text)
    if doc is None:
        return {"holes": [], "note": "no scene block"}
    hs = holes_of(doc)
    if not hs:
        return {"holes": [], "note": "no holes"}
    files = brand_files(brand, product)
    sys.path.insert(0, str(WS / "components" / "run-kit"))
    from run_kit import prompts as P
    tpl = P.latest(PROMPTS, "stage0d-slot-fill")
    sent = P.fill(Path(tpl).read_text(), {
        "brand": brand,
        "brand_files": "\n\n".join(f"### {n}\n\n{t}" for n, t in files.items()) or "(none on file)",
        "holes": "\n".join(_hole_text(h, doc) for h in hs)})
    if dry_run:
        print(sent)
        return {"holes": hs, "dry_run": True}
    if call is None:
        call = lambda p: research_call(p)
    reply = call(sent)
    d = json.loads(reply[reply.index("{"): reply.rindex("}") + 1])
    by = {r.get("id"): r for r in d.get("holes") or []}
    corpus = {n: _norm(t) for n, t in files.items()}
    changes, flagged = [], []
    for h in hs:
        r = by.get(h["id"]) or {}
        fill_words = str(r.get("fill") or "").strip()
        src = r.get("source") or "inferred"
        if src == "brand" and not (r.get("receipt") and any(_norm(r["receipt"]) in c for c in corpus.values())):
            src = "brand (receipt not in the core files — found elsewhere in the brand folder)"
        new_line = str(r.get("line") or "").strip() or h["line"].replace(h["hole"], fill_words, 1)
        new_line = HOLE.sub(fill_words, new_line).replace("  ", " ").strip()
        how = f"filled ({src}): {str(r.get('receipt') or '')[:160]}"
        sc = next(s for s in doc["scenes"] if s.get("id") == h["scene"])
        obj, key = sc, h["field"]
        if "." in key:
            a2, key = key.split(".", 1)
            obj = sc[a2]
        if h["index"] is None:
            obj[key] = new_line
        else:
            obj[key][h["index"]] = new_line
        text = text.replace(h["line"], new_line).replace(h["hole"], fill_words)
        changes.append({"scene": h["scene"], "field": h["field"], "was": h["line"], "now": new_line, "how": how, "source": src, "receipt": r.get("receipt")})
    for sc in doc["scenes"]:  # a cut never leaves an empty line on a card
        for k in ("card", "screen", "endcard"):
            if isinstance(sc.get(k), dict):
                for f in ("lines", "offer_lines"):
                    if isinstance(sc[k].get(f), list):
                        sc[k][f] = [x for x in sc[k][f] if str(x).strip()]
        if isinstance(sc.get("lines"), list):
            sc["lines"] = [x for x in sc["lines"] if str(x).strip()]
    m2, _ = _block(text)
    text = text[:m2.start(1)] + json.dumps(doc, indent=1, ensure_ascii=False) + text[m2.end(1):]
    text += ("\n\n## Holes filled from the brand's files (automatic, " + dt.date.today().isoformat() + ")\n\n"
             + "\n".join(f"- {c['scene']} · {c['field']}: {c['how']}\n  - now: \"{c['now']}\"" for c in changes) + "\n")
    if False:
        text += ("\n**Needs the owner — a card's own figure isn't in the brand's files:**\n\n"
                 + "\n".join(f"- {f['scene']} · {f['field']}: \"{f['line']}\"" + (f" — the files do have: {f['suggest']}" if f.get("suggest") else "") for f in flagged) + "\n")
    brief.write_text(text)
    document(brand, brief, doc, changes)
    return {"holes": hs, "changes": changes, "flagged": flagged}


def document(brand: str, brief: Path, doc: dict, changes: list[dict]) -> None:
    """the owner, 2026-09-23: "this type of research, especially with failed solutions,
    should be clearly documented in context folders for brands so whenever we call
    on these again in future briefs they are there." Every answer the fill found
    outside the core files goes into the proposal facts-found.md under
    runs/video-production/<brand>/research-proposals/; one that sits in a
    failed-solutions scene ALSO goes into failed-solutions.md there. A machine never
    writes brands/ (K2 (brands write wall)): a person commits accepted rows into
    brands/<brand>/intake/research/. Future fills read the brand's files and the open
    proposals first (brand_files). Append-only; nothing is overwritten."""
    new = [c for c in changes if not str(c.get("source", "")).startswith("brand") or "elsewhere" in str(c.get("source", ""))]
    if not new:
        return
    rdir = proposals_dir(brand)
    rdir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    try:
        where = str(brief.resolve().relative_to(WS))
    except ValueError:
        where = str(brief)
    secs = {s.get("id"): s.get("section") for s in doc.get("scenes") or []}

    def add(fname, title, intro, rows):
        f = rdir / fname
        head = "" if f.exists() else f"# {title}\n\n{intro}\n"
        f.write_text((f.read_text() if f.exists() else head) + "".join(rows))

    add("facts-found.md", "Facts found while filling briefs",
        "Answers the brief's hole-filler found outside the core product/offer/position files: from the rest of the brand folder, "
        "the web, or a sensible inference. Every future fill reads this file first, so nothing is researched twice. "
        "The brand's OWN price, guarantee and claims never come from here; they come from the product and offer files.\n",
        [f"\n- **{today}** · {c['scene']} ({secs.get(c['scene']) or '?'}) · source: {c.get('source')}\n"
         f"  - answer: \"{c['now']}\"\n  - receipt: {c.get('receipt') or '—'}\n  - brief: `{where}`\n" for c in new])
    fs = [c for c in new if secs.get(c["scene"]) == "failed-solutions"]
    if fs:
        add("failed-solutions.md", "Failed solutions: what the market already tried",
            "The alternatives our ads beat: what each one is, what it costs, why it fails for this customer, and the source. "
            "Filled automatically whenever a brief needs one; any brief reads it first.\n",
            [f"\n- **{today}** · \"{c['now']}\" · source: {c.get('source')} · {c.get('receipt') or '—'} · brief `{where}` scene {c['scene']}\n" for c in fs])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief"); ap.add_argument("--brand", required=True); ap.add_argument("--product"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    res = fill(Path(a.brief), a.brand, a.product, dry_run=a.dry_run)
    for c in res.get("changes") or []:
        print(f"{c['scene']} · {c['how']}\n    now: {c['now']}")
    for f in res.get("flagged") or []:
        print(f"NEEDS YOU  {f['scene']} · {f['field']}: {f['line']}" + (f" — the files do have: {f['suggest']}" if f.get("suggest") else ""))
    if not res.get("changes") and not a.dry_run:
        print(res.get("note", "nothing changed"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
