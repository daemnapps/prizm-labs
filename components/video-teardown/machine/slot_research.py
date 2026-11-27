"""SLOTS FILLED AT THE REWRITE, NOT ONLY AT THE BRIEF (2026-09-25).

owner: "I'm pretty sure I put in some sort of trigger for you to do deeper
research to fill in these gaps when necessary as well, specifically things
around the pricing of the other options" — and, when the rewrite still showed
"[SLOT: …]" for competitor prices: "if the research exists to put in real
prices you do it, stop asking."

The research step already existed, at the brief (video-production's
slotfill.py): brand files first, then the web, every fill with a receipt,
filed as a proposal under runs/video-production/<brand>/research-proposals/
(a person commits accepted rows into brands/<brand>/intake/research/;
K2 (brands write wall), SI-97 (brand research proposals))
and read back by every fill, so nothing is researched twice. This runs
the same research on the rewrite's own slots — every `[SLOT: …]` in the
injected script and its on-screen lines — right after stage 3, so the
expansion, the spice and the brief are built on real facts, not blanks.

A slot the research cannot fill with a receipt stays a slot (the manifest
blocks production on it). Brand-agnostic: it reads the run's brand files only.

    python3 slot_research.py <run dir>
"""
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
SLOT = re.compile(r"\[SLOT:[^\]]*\]")


def _slotfill():
    sp = importlib.util.spec_from_file_location(
        "slotfill", WS / "components" / "video-production" / "machine" / "slotfill.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def holes(text):
    """Every slot in the injected script (section 1), with the line it sits in."""
    m = re.search(r"(1\.\s*THE INJECTED SCRIPT.*?)(?=\n#*\s*\**2\.\s*DOMINANT|\Z)", text, re.S)
    return _markers(text, SLOT, m.start(1) if m else 0, m.end(1) if m else len(text))


def _markers(text, pattern, start, end):
    # Old runs appended documentation containing the original markers. Those are evidence.
    ledger = text.find("\n## Slots filled by research (automatic,")
    if ledger >= 0:
        end = min(end, ledger)
    out = []
    for match in pattern.finditer(text, start, end):
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        out.append({"id": f"H{len(out) + 1}", "hole": match.group(),
                    "line": text[line_start:line_end if line_end >= 0 else len(text)],
                    "start": match.start(), "end": match.end()})
    return out


PROMPT = """Fill the fact blanks for the brand {brand}. Each fact belongs to its specific product and line.
Copy the proposed fill verbatim from a literal, contiguous quote in a declared source.
Return the exact repo-relative source_path and the complete verbatim receipt containing that fill.
Use the named product's own source for product facts and its own row for prices. For people use the brand's casting record.
Open research proposals are leads only: locate and cite their underlying canonical source. A prior writer's version is not evidence.
For external research, search and read the original page. Return source web with its URL and literal receipt, so it can be independently verified.
Leave fill empty when the evidence is missing, ambiguous, or contradicts another source. Never paraphrase or convert a number.

Sources (full text):
{files}

Blanks (id · blank · entire source line):
{holes}

Answer with one JSON object only:
{{"holes":[{{"id":"H1","fill":"exact words","source":"brand | cast | web","source_path":"repo-relative file or URL","receipt":"exact quote"}}]}}"""


RESEARCH = re.compile(r"\[RESEARCH:[^\]]*\]")


def markers(text):
    """Every `[RESEARCH: …]` blank in a stage's output (the hooks pass, v16), with its line."""
    return _markers(text, RESEARCH, 0, len(text))


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _sources(sf, brand, product):
    files = dict(sf.brand_files(brand, product))
    cast = Path("runs", "casting", brand, "CAST.md").as_posix()
    if (WS / cast).is_file():
        files[cast] = (WS / cast).read_bytes().decode("utf-8")
    evidence = {}
    brand_root = (WS / "brands" / brand).resolve()
    for key in files:
        path = Path(key)
        if path.is_absolute() or ".." in path.parts:
            continue
        source = WS / path
        if not source.is_file():
            continue   # e.g. the public reader's THIS AD SELLS context
        data = source.read_bytes()
        files[key] = data.decode("utf-8")
        resolved = source.resolve()
        kind = "context"
        if resolved == (WS.resolve() / cast) and key == cast:
            kind = "cast"
        elif brand_root in resolved.parents and key.startswith(f"brands/{brand}/"):
            kind = "brand"
        evidence[key] = {"source": kind, "sha256": _sha(data)}
    return files, evidence


def _verify(row, files, sources):
    kind = row.get("source")
    key = row.get("source_path")
    quote = row.get("receipt")
    words = row.get("fill")
    if not isinstance(words, str) or not words.strip():
        return "No supported fill returned."
    if kind == "web":
        return "External candidate pending independent page capture and literal quote verification."
    if kind not in ("brand", "cast") or not isinstance(key, str) or key not in sources or sources[key]["source"] != kind:
        return "Cite an original declared brand or cast file; a proposal or undeclared path cannot support a fill."
    path = WS / key
    if not path.is_file() or _sha(path.read_bytes()) != sources[key]["sha256"]:
        return "The cited source changed after the request."
    if not isinstance(quote, str) or not quote.strip() or quote not in files[key]:
        return "The full receipt must occur verbatim in the cited source."
    if not re.search(r"(?<![\w.,])" + re.escape(words) + r"(?!\w|[.,]\d)", quote):
        return "The exact fill must occur as complete words in its quoted receipt."
    return None


def fill(run_dir, call=None, stage_file="3-injection.md", find=None):
    """Resolve each occurrence independently, retaining full run-local evidence."""
    d = Path(run_dir)
    st = json.loads((d / "run.json").read_text())
    brand, product = st.get("brand"), st.get("product")
    for name in (brand, stage_file, product or "unused"):
        if not isinstance(name, str) or name in ("", ".", "..") or Path(name).name != name:
            raise ValueError("Expected a brand, product or stage basename")
    inj = d / "stages" / stage_file
    original = inj.read_bytes()
    text = original.decode("utf-8")
    hs = (find or holes)(text)
    if not hs:
        return {"holes": 0, "filled": [], "pending": []}
    sf = _slotfill()
    files, sources = _sources(sf, brand, product)
    sent = PROMPT.format(brand=brand, files="\n\n".join(f"### {n}\n\n{t}" for n, t in files.items()),
                         holes="\n".join(f"{h['id']} · {h['hole']} · {h['line']}" for h in hs))
    evidence = d / "slot-research" / (Path(stage_file).stem + "-" + uuid.uuid4().hex)
    evidence.mkdir(parents=True)
    (evidence / "request.md").write_bytes(sent.encode())
    (evidence / "stage-before.md").write_bytes(original)
    manifest = {"schema": "slot-research/v1", "stage": stage_file, "before_sha256": _sha(original),
                "request_sha256": _sha(sent.encode()), "sources": sources, "state": "requested"}
    receipt = evidence / "receipt.json"
    def save():
        data = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
        receipt.write_bytes(data)
        (evidence / "receipt.sha256").write_text(_sha(data) + "  receipt.json\n")
    save()
    try:
        reply = (call or sf.research_call)(sent)
        (evidence / "reply.txt").write_bytes(reply.encode())
        manifest["reply_sha256"] = _sha(reply.encode())
        rows = json.loads(reply[reply.index("{"):reply.rindex("}") + 1])["holes"]
        if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in rows):
            raise ValueError("Unusable slot research response")
        got = {row["id"]: row for row in rows}
        if len(got) != len(rows):
            raise ValueError("Duplicate slot IDs in research response")
    except Exception as exc:
        manifest.update(state="unavailable", error_type=type(exc).__name__)
        save()
        raise
    filled, pending = [], []
    for h in hs:
        row = got.get(h["id"], {})
        reason = _verify(row, files, sources)
        if reason:
            pending.append({**h, "reason": reason, "candidate": row})
            continue
        key = row["source_path"]
        filled.append({**h, "fill": row["fill"], "source": row["source"], "source_path": key,
                       "receipt": row["receipt"], "source_sha256": sources[key]["sha256"],
                       "receipt_sha256": _sha(row["receipt"].encode()), "quote_offset": files[key].index(row["receipt"])})
    # Replace only verified source spans. Identically spelled blanks can have different answers.
    if inj.read_bytes() != original:
        manifest.update(state="stage_changed", filled=[], pending=pending)
        save()
        raise RuntimeError("Stage changed during slot research; inspect the receipt and rerun")
    for f in reversed(filled):
        assert text[f["start"]:f["end"]] == f["hole"]
        text = text[:f["start"]] + f["fill"] + text[f["end"]:]
    manifest.update(state="checked", after_sha256=_sha(text.encode()), filled=filled, pending=pending)
    save()
    if filled:
        tmp = inj.with_name("." + inj.name + "." + evidence.name + ".tmp")
        tmp.write_bytes(text.encode())
        os.replace(tmp, inj)
        # SI-97: verified proposals remain available for a person's review; machines never write brands/.
        proposal = WS / "runs" / "video-production" / brand / "research-proposals" / "facts-found.md"
        proposal.parent.mkdir(parents=True, exist_ok=True)
        with proposal.open("a") as out:
            for f in filled:
                out.write(f"- **{dt.date.today().isoformat()}** · {f['hole']} · {f['fill']} · "
                          f"source: {f['source_path']} · {f['receipt']} · run {d.name}\n")
    return {"holes": len(hs), "filled": filled, "pending": pending, "evidence": str(receipt.relative_to(d))}


if __name__ == "__main__":
    r = fill(sys.argv[1])
    print(f"{len(r['filled'])} of {r['holes']} slots filled")
    for f in r["filled"]:
        print(" ", f["hole"], "→", f["fill"])
