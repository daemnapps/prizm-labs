"""Does the email keep every promise it makes? Any brand, any product, any offer.

owner, 2026-10-18 (the sleeves email said "two steps", labelled STEP ONE and never showed STEP TWO, although the copy,
the design brief and the job card all carried the second step): "this is general awareness of the email itself, and
this must be clear and accomplished regardless of the brand / product / offer."

A reader model reads the built layout once, the way the customer will, against the job card and the copy, and lists
every promise the email sets up (a count or sequence, a thing named as part of the offer, a claim the job card says
it proves, a reference, a question raised, what the button says it does) and whether the email keeps it. The prompt
is prompts/design3-promises-v1-owner.md; it judges wholeness, never taste.

    check(run_dir, spec=None, job=None, copy=None) -> {"promises": [...], "broken": [...]}   writes design/promises.json
    python3 components/email-production/design/promises.py runs/email-production/<brand>/<label>

The layout step (line.py) rewrites a layout that breaks a promise; the gap filler (gaps.py) reads design/promises.json
and sends a broken promise to a redesign with its fix named, before any person sees the email.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EM = HERE.parent
REPO = EM.parents[1]
PROMPT = EM / "prompts" / "design3-promises-v1-owner.md"
SKIP = {"s", "link", "gif", "photo", "proof", "source", "use", "ratio", "focus", "brief", "todo", "product", "theme",
        "record", "pins", "history", "stage", "fill", "cy"}


def layout_text(spec):
    """The email as built, section by section: its words and what its pictures show, nothing else."""
    out = []
    def walk(x, words, pics):
        if isinstance(x, dict):
            if "alt" in x or "todo" in x:
                pics.append(x.get("alt") or x.get("todo") or "")
            for k, v in x.items():
                if k in SKIP or k == "alt":
                    continue
                if isinstance(v, str) and v.strip():
                    words.append(re.sub(r"<[^>]+>", "", v))
                else:
                    walk(v, words, pics)
        elif isinstance(x, list):
            for v in x:
                if isinstance(v, str):         # lines kept as a list are words too (2026-10-18: a guarantee line was
                    if v.strip():              # missed this way and reported as a bare "60 DAYS")
                        words.append(re.sub(r"<[^>]+>", "", v))
                else:
                    walk(v, words, pics)
    for i, s in enumerate(spec.get("sections", [])):
        words, pics = [], []
        walk(s, words, pics)
        out.append("[%d] %s\n  words: %s%s" % (i + 1, s.get("s"), " | ".join(words) or "(none)",
                                               ("\n  pictures: " + " | ".join(pics)) if pics else ""))
    return "\n".join(out)


FUNNEL_ONLY = re.compile(r"funnels? and (its|their) ads|funnel only|funnel-only|only on the funnel|never in an email", re.I)


def funnel_only(block):
    """An offer-bank block the bank keeps for the funnel and its ads (said in its opening lines): never an email's."""
    return bool(FUNNEL_ONLY.search(block[:600]))


FUNNEL_LINE = re.compile(r"^\s*-\s*(sold in the \S+ funnel|funnel offer\b)", re.I)


def email_lines(block):
    """An offer block as an email may read it: lines the bank gives to the funnel alone are taken out."""
    return "\n".join(l for l in block.splitlines() if not FUNNEL_LINE.search(l) and not FUNNEL_ONLY.search(l))


def send_offers(run_dir):
    """The offers this send was written to carry: --offer and --offer-also from the run's copy-argv.json."""
    try:
        a = json.loads((Path(run_dir) / "copy-argv.json").read_text())
    except (OSError, ValueError):
        return []
    a = a if isinstance(a, list) else a.get("argv", [])
    out = []
    for flag in ("--offer", "--offer-also"):
        for i, x in enumerate(a[:-1]):
            if x == flag:
                out += [v.strip() for v in str(a[i + 1]).split(",") if v.strip() and v.strip().lower() != "none"]
    return list(dict.fromkeys(out))


def rulings(run_dir, spec):
    """The decisions that outrank the job card: this occasion's offer-bank block and the chain's learnings."""
    out = []
    brand = spec.get("brand") or Path(run_dir).parent.name
    try:
        rj = json.loads((Path(run_dir) / "run.json").read_text())
    except (OSError, ValueError):
        rj = {}
    occ = ((rj.get("assignment") or {}).get("occasion") or "").split(" ")[0].lower()
    f = REPO / "brands" / brand / "products" / "offer-bank.md"
    own = send_offers(run_dir)
    if f.is_file():
        blocks = re.split(r"\n#{2,3} ", f.read_text())[1:]
        # the send's OWN offer outranks everything (2026-11-08): the occasion's block used to stand in for it, and
        # brand_b's `black-friday` block is the funnel's 3-pack, so single-product emails got the funnel deal back
        for key in own:
            for block in blocks:
                if block.split("\n", 1)[0].lower().split(" ")[0] == key.lower():
                    out.append("THE OFFER THIS SEND CARRIES (offer bank, `%s`):\n" % key + email_lines(block.strip())[:6000])
        if occ:
            for block in blocks:
                head = block.split("\n", 1)[0].lower()
                if head.startswith(occ) and head.split(" ")[0] not in [k.lower() for k in own] and not funnel_only(block):
                    out.append(("THE OCCASION (offer bank; context only, the send's own offer above wins):\n" if own
                                else "THE OFFER FOR THIS OCCASION (offer bank):\n") + block.strip()[:6000])
    try:
        sys.path.insert(0, str(REPO / "components" / "run-kit"))
        from run_kit import learnings as LN
        b = LN.block(brand, ("copy", "design", "picture"))
        if b and b != "(none yet)":
            out.append("RULES FROM PAST REVIEWS:\n" + b[:8000])
    except Exception:  # noqa: BLE001
        pass
    return "\n\n".join(out) or "(none)"


def lean():
    """../lean_call.py (LD-62 (lean model calls)), loaded by file for the whole design line. That folder
    never goes on the path here: its paths.py would shadow marketing-calendar's (LD-19 (calendar shadow fix))."""
    m = sys.modules.get("lean_call")
    if m is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("lean_call", EM / "lean_call.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["lean_call"] = m
        spec.loader.exec_module(m)
    return m


def check(run_dir, spec=None, job=None, copy=None):
    run_dir = Path(run_dir)
    d = run_dir / "design"
    spec = spec or json.loads((d / "email.json").read_text())
    job = job or spec.get("job") or (json.loads((d / "job.json").read_text()) if (d / "job.json").is_file() else {})
    if copy is None:
        f = run_dir / "deliverable" / "email.json"
        copy = json.loads(f.read_text()) if f.is_file() else {}
    sys.path.insert(0, str(REPO / "components" / "run-kit"))
    from run_kit import model as M
    lean_call = lean()
    p = PROMPT.read_text()
    for k, v in (("rulings", rulings(run_dir, spec)), ("job", json.dumps(job, indent=1, ensure_ascii=False)), ("copy", json.dumps(copy, indent=1, ensure_ascii=False)[:30000]),
                 ("layout", layout_text(spec))):
        p = p.replace("{%s}" % k, v)
    (d / "design3--prompt.md").write_text(p)
    model, _ = M.pick("checks", len(p))
    text = M.call(p, model, label="design3-" + run_dir.name, runner=lean_call.design_runner(M))
    m = re.search(r"\{.*\}", text, re.S)
    try:
        got = json.loads(m.group(0)) if m else {}
    except ValueError:
        got = {}
    rows = got.get("promises") or []
    out = {"model": model, "promises": rows, "broken": [r for r in rows if r.get("kept") is False]}
    (d / "promises.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    return out


def problems(result):
    """Broken promises as layout problems, in the words the rewrite reads."""
    return ["a broken promise: %s (sections %s) — missing: %s. Fix: %s" % (
        r.get("promise"), r.get("where"), r.get("missing"), r.get("fix")) for r in result.get("broken", [])]


if __name__ == "__main__":
    for r in sys.argv[1:]:
        res = check(r)
        print("%s  %d promises · %d broken" % (Path(r).name, len(res["promises"]), len(res["broken"])))
        for x in res["promises"]:
            print("   %s %s%s" % ("kept  " if x.get("kept") else "BROKEN", x.get("promise"), "" if x.get("kept") else " — " + str(x.get("missing"))))
