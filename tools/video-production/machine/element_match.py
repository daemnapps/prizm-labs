"""A BANKED ELEMENT IS REUSED ONLY IF IT MATCHES THIS BRIEF (2026-10-01).

the owner: "the whole point of doing all that work at the very start is to get
everything down before we even go into production … we generate all the
elements for the cast and everything that's based off the brief."

the three-doctors run reused people and places made for an earlier brief; nothing
checked them against the new one (THE-CHAIN.md, "Why this page exists"). This
reads, for every person and place the brief binds to a bank folder, the
brief's own description beside the bank's record, and asks one question of a
model per element: does the banked element match what the brief describes —
who or what it is, gender and age, the kind of place, the look? A difference
in detail the brief does not ask for is not a mismatch.

    python3 element_match.py <brief.md> --brand <brand>

Writes nothing; returns [{kind, id, bank_id, verdict, why}]. Brand-agnostic.
"""
import argparse, importlib.util, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]


def _gemini():
    sp = importlib.util.spec_from_file_location("gb", WS / "tools/video-teardown/tools/gemini_breakdown.py")
    g = importlib.util.module_from_spec(sp); sp.loader.exec_module(g)
    return g


def ask(prompt, model="gemini-3.1-pro-preview"):
    g = _gemini(); k = g.key()
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    r = g.req(f"{g.BASE}/v1beta/models/{model}:generateContent?key={k}",
              data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
    return json.loads(re.search(r"\{.*\}", t, re.S).group(0))


PROMPT = """A video brief needs one {kind}. The brief describes it as:

{brief}

The production bank already holds a {kind} under the id "{bank_id}". Its record:

{bank}

Does the banked {kind} match what the brief describes? Judge only what the brief
asks for: for a person — gender, age range, ethnicity or look where the brief
names it, the role; for a place — the kind of place (what business, inside or
outside), its key dressing, the light. Extra detail the brief does not mention
is fine. Readable words, signs, lettering and logos are never in a banked
place — they are laid over later — so their absence is not a mismatch. A different gender, a different kind of place, a clearly different
age or look the brief names is a MISMATCH.

Answer JSON only: {{"verdict": "MATCH" or "MISMATCH", "why": "one short sentence"}}"""


def bank_record(brand, kind, bank_id):
    base = WS / "runs" / "ai-elements" / brand / ("casting" if kind == "person" else "sets") / bank_id
    for name in ("character.md", "set.md", "spec.json"):
        f = base / name
        if f.exists():
            return f.read_text()[:4000]
    return ""


def check(brief_path, brand):
    body = Path(brief_path).read_text()
    doc = json.loads(re.findall(r"```json\s*\n(.*?)\n```", body, re.S)[-1])
    out = []
    items = [("person", c["id"], c.get("bank_id"), c.get("identity_block") or "") for c in doc.get("cast") or []]
    items += [("place", w["id"], w.get("bank_id"),
               f"{w.get('description') or ''} Dressing: {', '.join(w.get('dressing') or [])}. Light: {w.get('light') or ''}")
              for w in doc.get("world") or []]
    for kind, eid, bid, desc in items:
        if not bid or str(bid).upper() == "NEW":
            out.append({"kind": kind, "id": eid, "bank_id": bid, "verdict": "TO MAKE", "why": "not in the bank yet"})
            continue
        if kind == "place":
            v = visual(brief_path, doc, eid, brand, bid)
            if v and v["verdict"] != "MATCH":
                out.append({"kind": kind, "id": eid, "bank_id": bid, **v}); continue
            # the picture can match the swipe while the brief's WORDS describe
            # another room (2026-10-02, QC B3: the brief said wallpaper, the bank
            # and the swipe a tiled wall) — the words are checked against the bank too
        rec = bank_record(brand, kind, bid)
        if not rec:
            out.append({"kind": kind, "id": eid, "bank_id": bid, "verdict": "MISSING", "why": "no record in the bank folder"})
            continue
        try:
            a = ask(PROMPT.format(kind=kind, brief=desc, bank_id=bid, bank=rec))
        except Exception as e:
            a = {"verdict": "UNCHECKED", "why": f"the check could not run ({type(e).__name__})"}
        if kind == "person" and a.get("verdict") == "MATCH":
            lb = re.search(rf"^\*\*{re.escape(eid)}\*\* —.*?\nLoad-bearing:\s*([^\n]+)", body, re.S | re.M)
            pic = WS / "runs" / "ai-elements" / brand / "casting" / bid / "master.jpg"
            if lb and pic.exists():
                a = load_bearing(pic, lb.group(1)) or a
        out.append({"kind": kind, "id": eid, "bank_id": bid, **a})
    out += brief_follows(body, doc, brand)
    return out


def load_bearing(picture, detail):
    """THE PICTURE CARRIES WHAT THE AD IS ABOUT (2026-10-02, QC B1: the brief's
    whole ad is the spots on her face; the banked face had none — they were on
    her arms from an earlier brief, and every text check passed). The person's
    master is looked at against the brief's Load-bearing line; three asks, the
    majority wins. None when the check cannot run."""
    sp = importlib.util.spec_from_file_location("vt_deepen", WS / "tools/video-teardown/machine/deepen.py")
    dp = importlib.util.module_from_spec(sp); sp.loader.exec_module(dp)
    q = ("This is the reference picture of a person a video ad will be made from. The ad needs, visibly, this "
         f"load-bearing detail: \"{detail}\". Judge ONLY what a head-and-shoulders reference portrait can carry: the "
         "face, the skin of the face, the hair. Ignore hands, arms, sleeves, clothes, jewellery hidden by hair, props, "
         "poses and actions — those are staged in each shot. If the detail has nothing about the face, its skin or the "
         "hair, answer MATCH. Is the face/skin/hair part visible in this picture? Answer MATCH or MISMATCH, then one "
         "sentence naming what is missing.")
    try:
        answers = [dp.ask(str(picture), q).strip() for _ in range(3)]
    except Exception:
        return None
    bad = [x for x in answers if x.upper().startswith("MISMATCH")]
    a = bad[0] if len(bad) >= 2 else next(x for x in answers if not x.upper().startswith("MISMATCH"))
    verdict = "MISMATCH" if a.upper().startswith("MISMATCH") else "MATCH"
    return {"verdict": verdict, "why": "the picture against the load-bearing detail: " + re.sub(r"^(MATCH|MISMATCH)\W*", "", a, flags=re.I)[:200]}


def brief_follows(body, doc, brand):
    """The other direction (the owner, 2026-10-01, "did the brief follow the
    element?"): every word in the brief about a person — the readable cast
    block and every scene's directions — must describe that person as their
    element is. Doctor 3 was bound to a man while the brief still said "low
    bun, pearl studs … turns her hand over", and only the JSON line was
    compared. No model: the teardown machine's cast check, reused."""
    spec = importlib.util.spec_from_file_location(
        "cast_match", WS / "tools" / "video-teardown" / "machine" / "cast_match.py")
    cm = importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)
    rows = []
    for f in cm.readable_mismatches(body, doc, brand) + cm.scene_mismatches(doc, brand):
        rows.append({"kind": "brief", "id": f["n"], "bank_id": "", "verdict": "MISMATCH",
                     "why": f"{f['element']} — {f['why']}"})
    return rows


def visual(brief_path, doc, eid, brand, bid):
    """A place is judged by picture: its banked wide plate beside the swipe frame
    the brief says it recreates. The brief's words are the brief's reading of
    that frame; the frame is the truth. None when there is no frame to compare."""
    import subprocess, tempfile
    w = next((x for x in doc.get("world") or [] if x.get("id") == eid), {})
    ts = [int(a) * 60 + float(b) for a, b in re.findall(r"(\d+):(\d+(?:\.\d+)?)", w.get("real_reference") or "")]
    m = bool(ts)
    src = Path(brief_path).resolve().parent.parent / "source.mp4"
    plate = WS / "runs" / "ai-elements" / brand / "sets" / bid / "plates" / "wide.jpg"
    if not (m and src.exists() and plate.exists()):
        return None
    # a SPAN ("0:49–1:16") is judged at its middle, clear of transitions; a LIST of
    # moments ("0:15.6, 0:39.7 and 1:04.5") at its first moment — the middle of two
    # listed moments is some other shot (2026-10-02: it landed in another room)
    span = re.search(r"(\d+):(\d+(?:\.\d+)?)\s*[–-]\s*(\d+):(\d+(?:\.\d+)?)", w.get("real_reference") or "")
    if span:
        a_, b_ = int(span.group(1)) * 60 + float(span.group(2)), int(span.group(3)) * 60 + float(span.group(4))
        t = (a_ + b_) / 2
    else:
        t = ts[0] + (0.3 if len(ts) > 1 else 1.0)
    d = Path(tempfile.mkdtemp())
    try:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", str(src), "-frames:v", "1",
                        "-vf", "scale=-2:640", str(d / "a.jpg")], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(plate), "-vf", "scale=-2:640", str(d / "b.jpg")], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(d / "a.jpg"), "-i", str(d / "b.jpg"),
                        "-filter_complex", "hstack", str(d / "pair.jpg")], check=True)
        sp = importlib.util.spec_from_file_location("vt_deepen", WS / "tools/video-teardown/machine/deepen.py")
        dp = importlib.util.module_from_spec(sp); sp.loader.exec_module(dp)
        Q = ("LEFT is a frame from a real video (ignore the people and anything they hold or wear — "
                   "a phone, a tool, a bag are props, not the place — and ignore any words, "
                   "signs or lettering — those are laid over later). RIGHT is an empty place built to recreate it. Is "
                   "RIGHT recognisably the same kind of place with the same key features (walls, fixtures, furniture, "
                   "screen, light)? Answer MATCH or MISMATCH, then one sentence naming any key feature missing or wrong.")
        # the judge flips on small details from one call to the next (2026-10-02:
        # the same sidewalk plate MATCH, MISMATCH, MATCH) — three asks, the majority wins
        answers = [dp.ask(str(d / "pair.jpg"), Q).strip() for _ in range(3)]
        bad = [x for x in answers if x.upper().startswith("MISMATCH")]
        a = bad[0] if len(bad) >= 2 else next(x for x in answers if not x.upper().startswith("MISMATCH"))
    except Exception as e:
        return {"verdict": "UNCHECKED", "why": f"the picture check could not run ({type(e).__name__})"}
    verdict = "MISMATCH" if a.upper().startswith("MISMATCH") else "MATCH"
    return {"verdict": verdict, "why": "judged against the swipe frame: " + re.sub(r"^(MATCH|MISMATCH)\W*", "", a, flags=re.I)[:200]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("brief"); ap.add_argument("--brand", required=True)
    a = ap.parse_args()
    for r in check(a.brief, a.brand):
        print(f"{r['verdict']:<9} {r['kind']:<6} {r['id']:<20} → {r['bank_id']}: {r['why']}")
