"""SLOTS FILLED AT THE REWRITE, NOT ONLY AT THE BRIEF (2026-09-25).

the owner: "I'm pretty sure I put in some sort of trigger for you to do deeper
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
import datetime as dt, importlib.util, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
SLOT = re.compile(r"\[SLOT:[^\]]*\]")


def _slotfill():
    sp = importlib.util.spec_from_file_location(
        "slotfill", WS / "tools" / "video-production" / "machine" / "slotfill.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def holes(text):
    """Every slot in the injected script (section 1), with the line it sits in."""
    m = re.search(r"(1\.\s*THE INJECTED SCRIPT.*?)(?=\n#*\s*\**2\.\s*DOMINANT|\Z)", text, re.S)
    part = m.group(1) if m else text
    out = []
    for line in part.splitlines():
        for s in SLOT.findall(line):
            out.append({"id": f"H{len(out) + 1}", "hole": s, "line": line.strip()})
    return out


PROMPT = """You are filling the blanks a rewrite of an ad left, for the brand "{brand}".

Each blank is a fact the rewrite needed and did not have: a price, a name, a number, a credential.
Fill each one from, in this order:
1. the brand's own files below (quote the exact words you used as the receipt);
2. the brand's folder (brands/{brand}/ — read, grep, glob);
3. the open web (search and read real pages; the receipt is the page's own words plus its URL).
Never invent a number or a person. A blank you cannot fill with a receipt comes back with "fill": "".
Use the brand's banked people where a name or age is asked for (runs/casting/{brand}/CAST.md).

The brand's files:
{files}

The blanks (id · the blank · the line it sits in):
{holes}

Answer with ONE JSON object and nothing else:
{{"holes": [{{"id": "H1", "fill": "<the words that replace the blank, or empty>", "source": "brand | web | cast", "receipt": "<the exact words it came from, with the URL for the web>"}}]}}"""


RESEARCH = re.compile(r"\[RESEARCH:[^\]]*\]")


def markers(text):
    """Every `[RESEARCH: …]` blank in a stage's output (the hooks pass, v16), with its line."""
    out = []
    for line in text.splitlines():
        for s in RESEARCH.findall(line):
            out.append({"id": f"H{len(out) + 1}", "hole": s, "line": line.strip()})
    return out


def fill(run_dir, call=None, stage_file="3-injection.md", find=None):
    """Research the blanks in a stage's output. The rewrite's `[SLOT: …]`s by
    default; the hooks pass's `[RESEARCH: …]` blanks with find=markers."""
    d = Path(run_dir)
    st = json.loads((d / "run.json").read_text())
    brand, product = st.get("brand"), st.get("product")
    inj = d / "stages" / stage_file
    text = inj.read_text()
    hs = (find or holes)(text)
    if not hs:
        return {"holes": 0, "filled": []}
    sf = _slotfill()
    files = sf.brand_files(brand, product)
    sent = PROMPT.format(brand=brand, files="\n\n".join(f"### {n}\n\n{t}" for n, t in files.items())[:60000],
                         holes="\n".join(f"{h['id']} · {h['hole']} · {h['line'][:400]}" for h in hs))
    reply = (call or sf.research_call)(sent)
    got = {r.get("id"): r for r in json.loads(reply[reply.index("{"): reply.rindex("}") + 1]).get("holes") or []}
    filled = []
    for h in hs:
        r = got.get(h["id"]) or {}
        words = str(r.get("fill") or "").strip()
        if not words or not str(r.get("receipt") or "").strip():
            continue
        text = text.replace(h["hole"], words)
        text = re.sub(r"\b([Tt]he) [Tt]he\b", r"\1", text)   # a fill's own "The" after the format's "the"
        filled.append({**h, "fill": words, "source": r.get("source"), "receipt": r.get("receipt")})
    if filled:
        text = text.rstrip() + ("\n\n## Slots filled by research (automatic, " + dt.date.today().isoformat() + ")\n\n"
                                + "\n".join(f"- {f['hole']} → \"{f['fill']}\" ({f['source']}): {str(f['receipt'])[:220]}" for f in filled) + "\n")
        inj.write_text(text)
        rdir = sf.proposals_dir(brand)
        rdir.mkdir(parents=True, exist_ok=True)
        ff = rdir / "facts-found.md"
        head = "" if ff.exists() else ("# Facts found — filled into our scripts from research\n\n"
                                       "Every fill carries its receipt. Every future fill reads this file first.\n\n")
        with ff.open("a") as fh:
            fh.write(head + "".join(f"- **{dt.date.today().isoformat()}** · {f['hole'].split(':', 1)[-1][:-1].strip()} · \"{f['fill']}\" · "
                                    f"source: {f['source']} · {str(f['receipt'])[:300]} · run {d.name}\n" for f in filled))
    return {"holes": len(hs), "filled": filled}


if __name__ == "__main__":
    r = fill(sys.argv[1])
    print(f"{len(r['filled'])} of {r['holes']} slots filled")
    for f in r["filled"]:
        print(" ", f["hole"], "→", f["fill"])
