"""SWIPE MATCH — the last check before a brief can reach production (2026-09-24).

the owner, after a rewrite moved a swipe's offices to other rooms and turned its
selfie opener into a composed shot: "literally this cannot happen again UNLESS
I DISCRETELY SAY SO. THE WHOLE POINT IS TO TAKE A SWIPE AND ADAPT, not ruin
it" — then, before batching many videos for many brands: "make sure this never
happens again, literally."

The stage-3 lock asks the rewrite to own up to its changes; this does not
trust it. A judge compares the FINISHED brief with the swipe's own teardown,
shot by shot — place, people, camera, who speaks, order — and every change is
numbered M1, M2, …. Any change not approved by the owner (`--approve-structure
M2` or `all`) HOLDS the brief, and the brief carries a stamp on its first line
that production reads: no `swipe-match: PASSED` stamp, no production.

The findings are kept in `swipe-match.json` beside the run, keyed to the
brief's hash, so an approval re-checks the SAME findings — the judge is not
asked again and the numbers he approved never move. Brand-agnostic: it reads
only the run's own teardown and brief.

    python3 swipe_match.py <run dir> [--approve-structure M1,M2|all]
"""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# the writing station's prompts live in the copywriter since 2026-09-30
PROMPTS = next((d for d in (HERE.parents[1] / "copywriter" / "prompts" / "video" / "stage-5m-swipe-match",
                           HERE.parent / "prompts" / "stage-5m-swipe-match") if d.is_dir()),
               HERE.parents[1] / "copywriter" / "prompts" / "video" / "stage-5m-swipe-match")
GEMINI = HERE.parent / "tools" / "gemini_text.py"
MODEL = "gemini-3.1-pro-preview"   # the strongest reader we hold; flash passed a doctor turned into a shop assistant
STAMP = re.compile(r"^<!-- swipe-match: [^\n]*-->\n", re.M)
READ = re.compile(r"^<!-- brief-read: [^\n]*-->\n", re.M)


def prompt_file():
    files = sorted(PROMPTS.glob("swipe-match-v*-damon.md"),
                   key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    if not files:
        raise RuntimeError(f"no swipe-match prompt in {PROMPTS}")
    return files[-1]


MANIFEST_BLOCK = re.compile(r"\n?<!-- manifest -->.*?<!-- /manifest -->\n?", re.S)


def unstamped(text):
    """The brief without its two stamp lines (swipe match, the owner's read) and
    without the manifest block at its end (manifest.py) — none of them is the brief."""
    text = MANIFEST_BLOCK.sub("\n", text)
    for _ in range(2):
        if text.startswith("<!-- swipe-match:"):
            text = STAMP.sub("", text, count=1)
        elif text.startswith("<!-- brief-read:"):
            text = READ.sub("", text, count=1)
    return text


def brief_hash(brief_text):
    """The brief's fingerprint, blind to what the elements BIND step writes
    (each person's and place's bank_id, each scene's look ids) — pointing a
    role at its banked person is not a change to the swipe. Any other edit is."""
    text = unstamped(brief_text).rstrip() + "\n"   # a trailing blank line is not an edit
    blocks = list(re.finditer(r"```json\s*\n(.*?)\n```", text, re.S))
    if blocks:
        try:
            doc = json.loads(blocks[-1].group(1))
            for key in ("cast", "world"):
                for row in doc.get(key) or []:
                    row.pop("bank_id", None)
            for sc in doc.get("scenes") or []:
                sc.pop("looks", None)
            b = blocks[-1]
            text = text[:b.start(1)] + json.dumps(doc, sort_keys=True, ensure_ascii=False) + text[b.end(1):]
        except Exception:
            pass
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def teardown_part(teardown):
    """The shot table and the scene contracts — what the swipe IS on screen.
    The psychology and voice sections are not structure."""
    m = re.search(r"(###\s*1\..*?)(?=###\s*3\.|\Z)", teardown, re.S)
    part = m.group(1) if m else teardown
    fm = re.search(r"###\s*THE FRAME MAP.*\Z", teardown, re.S)
    if fm and fm.group(0) not in part:
        part += "\n\n" + fm.group(0)
    return part


def _gemini_tools():
    import importlib.util as u
    sp = u.spec_from_file_location("gemini_breakdown", HERE.parent / "tools" / "gemini_breakdown.py")
    m = u.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def ask_judge(teardown, brief, video=None):
    """The judge WATCHES the swipe when the run holds it (source.mp4) — the
    teardown's notes can be wrong, and a brief that copied a wrong note
    would pass a text-only check."""
    pf = prompt_file()
    text = (pf.read_text()
            .replace("{teardown_record}", teardown_part(teardown))
            .replace("{brief}", unstamped(brief)))
    if not (video and Path(video).exists()):
        raise RuntimeError("the swipe video is not in the run — the swipe match watches it, "
                           "it never trusts the notes alone")
    g = _gemini_tools()
    k = g.key()
    uri, mime = g.upload_cached(k, Path(video))
    last = ""
    for _ in range(3):
        try:
            r = g.req(f"{g.BASE}/v1beta/models/{MODEL}:generateContent?key={k}",
                      data=json.dumps({"contents": [{"parts": [
                          {"file_data": {"file_uri": uri, "mime_type": mime}},
                          {"text": text}]}],
                          "generationConfig": {"responseMimeType": "application/json", "temperature": 0, "seed": int(os.environ.get("DAEMN_SWIPE_SEED", "7"))}}).encode(),
                      headers={"Content-Type": "application/json"})
            raw = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
            m = re.search(r"\{.*\}", raw, re.S)
            return json.loads(m.group(0)), pf.name
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:300]}"
    raise RuntimeError(f"the swipe-match judge could not answer — {last}")


def vote(teardown, brief, video, n=3):
    """THREE READS, TWO MUST AGREE (2026-09-24). One read of a video judge
    flipped between runs on an unchanged brief — a gate that flips jams a batch
    of hundreds. Each shot is flagged only when at least two of three reads
    flag it; an added scene is out of the world only when two of three say so."""
    import os as _os
    reads = []
    for seed in (7, 11, 13)[:n]:
        _os.environ["DAEMN_SWIPE_SEED"] = str(seed)
        v, pname = ask_judge(teardown, brief, video)
        reads.append(v)
    need = n // 2 + 1
    def key(sh):
        return re.sub(r"\s+", "", str(sh.get("swipe", "")))
    base = reads[0]
    shots = []
    for sh in base.get("shots", []):
        same = [next((x for x in r.get("shots", []) if key(x) == key(sh)), None) for r in reads]
        flagged = [x for x in same if x and (x.get("changed") or x.get("keeps") is False)]
        if len(flagged) >= need:
            pick = max(flagged, key=lambda x: len(x.get("changed") or []))
            shots.append({**pick, "keeps": False, "votes": f"{len(flagged)}/{n}"})
        else:
            shots.append({**sh, "keeps": True, "changed": [], "votes": f"{len(flagged)}/{n}"})
    added = []
    for a in base.get("added", []):
        same = [next((x for x in r.get("added", []) if x.get("brief_scene") == a.get("brief_scene")), None) for r in reads]
        out = [x for x in same if x and x.get("in_world") is False]
        added.append({**a, "in_world": len(out) < need, "votes": f"{len(out)}/{n}"})
    return {"shots": shots, "added": added, "reads": n}, pname


SELFIE = re.compile(r"selfie|arm'?s[- ]length|holding (the|her|his|their) phone|phone in (her|his|their) hand", re.I)


def camera_backstop(verdict, teardown, brief):
    """Not left to the judge: a swipe shot whose teardown camera is a selfie
    must land on brief scenes whose own words say selfie. Adds the change to
    the judge's row when they do not."""
    try:
        scenes = {s["id"]: s for s in json.loads(re.search(r"```json\n(.*?)\n```", unstamped(brief), re.S).group(1))["scenes"]}
    except Exception:
        return
    for sh in verdict.get("shots", []):
        if not SELFIE.search(sh.get("swipe_has", "")):
            continue
        for sid in sh.get("brief_scenes", []):
            sc = scenes.get(sid)
            if sc is None or sc.get("kind") in ("card", "endcard"):
                continue        # a graphic laid over a selfie row is a graphic, not a camera (2026-10-01)
            own = json.dumps({k: sc.get(k) for k in ("first_frame", "last_frame", "happens", "beats")}, ensure_ascii=False)
            if not SELFIE.search(own):
                sh["keeps"] = False
                sh.setdefault("changed", []).append(
                    f"camera: the swipe shot is a selfie; brief {sid} never says selfie (machine check, not the judge)")


def number(verdict):
    """Every change gets a number, in swipe order, then the added scenes."""
    out, n = [], 0
    for s in verdict.get("shots", []):
        if s.get("keeps") and not s.get("changed"):
            continue
        n += 1
        out.append({"n": f"M{n}", "swipe": s.get("swipe", ""),
                    "brief_scenes": s.get("brief_scenes", []),
                    "swipe_has": s.get("swipe_has", ""), "brief_has": s.get("brief_has", ""),
                    "changed": s.get("changed") or ["unspecified"]})
    for a in verdict.get("added", []):
        if a.get("in_world") is True:
            continue      # an expansion beat inside the swipe's places, people and cameras
        n += 1
        out.append({"n": f"M{n}", "swipe": "(none)", "brief_scenes": [a.get("brief_scene", "")],
                    "swipe_has": "nothing", "brief_has": a.get("what", ""),
                    "changed": ["added outside the swipe's world: " + str(a.get("place") or "a new place, person or camera")]})
    return out


def approved():
    v = os.environ.get("DAEMN_STRUCTURE_APPROVALS", "").strip()
    return "all" if v.lower() == "all" else {x.strip() for x in v.split(",") if x.strip()}



def teardown_stage(d, name):
    """A teardown stage file for this run. The writing chain files its run apart
    from the swipe's teardown (runs/video-writing/ beside runs/video-teardown/,
    same brand and label), so a stage not in this run is read from its
    teardown twin (2026-10-07)."""
    d = Path(d)
    p = d / "stages" / name
    if p.exists() or d.resolve().parent.parent.name != "video-writing":
        return p
    twin = d.resolve().parent.parent.parent / "video-teardown" / d.resolve().parent.name / d.name / "stages" / name
    return twin if twin.exists() else p

def check(run_dir, brief_name="5-brief.md"):
    """Returns (passed, open_findings). Writes swipe-match.json, SWIPE-MATCH.md
    when anything is open, and the stamp on the brief's first line."""
    d = Path(run_dir)
    brief_p = d / "stages" / brief_name
    teardown_p = teardown_stage(d, "1-teardown.md")
    brief = brief_p.read_text()
    h = brief_hash(brief)
    rec_p = d / "swipe-match.json"
    rec = json.loads(rec_p.read_text()) if rec_p.exists() else {}
    # THE FRAME MAP IS THE SWIPE, SHOT BY SHOT (2026-10-02): the record's table
    # is rounded to the second and can miss a person in a two-second shot or
    # name the wrong wall; the judge reads the frame map beside it, and a new
    # frame map is a reason to judge again
    fm_p = d / "framemap" / "FRAME-MAP.md"
    fm_text = fm_p.read_text() if fm_p.exists() else ""
    fm_key = hashlib.md5(fm_text.encode()).hexdigest()[:12] if fm_text else ""
    if rec.get("brief_hash") != h or rec.get("frame_map", "") != fm_key:
        if not teardown_p.exists():
            raise RuntimeError("no teardown record — a brief with no swipe behind it cannot be matched")
        record = teardown_p.read_text()
        if fm_text:
            record = (record + "\n\n### THE FRAME MAP — every shot, moment by moment (where it and the table "
                      "above disagree, the frame map is the swipe)\n\n" + fm_text)
        src = d / "source.mp4"
        if not src.exists():   # a split writing run: the swipe the run.json names
            rj = d / "run.json"
            v = json.loads(rj.read_text()).get("video") if rj.exists() else None
            src = Path(v) if v and Path(v).exists() else teardown_stage(d, "../source.mp4")
        verdict, pname = vote(record, brief, src)
        for sh in verdict.get("shots", []):
            sh["judge_keeps"] = sh.get("keeps")          # the judge's own word, kept apart from the machine checks
        camera_backstop(verdict, teardown_p.read_text(), brief)
        rec = {"brief_hash": h, "prompt": pname, "model": MODEL, "frame_map": fm_key,
               "verdict": verdict, "findings": number(verdict)}
    elif teardown_p.exists():
        # the judge's answer is reused; the machine checks are not — they are
        # re-run, so a fix to a check applies to a brief already judged (2026-10-01)
        for sh in rec["verdict"].get("shots", []):
            ch = [c for c in sh.get("changed") or [] if "(machine check, not the judge)" not in c]
            if "judge_keeps" not in sh:
                sh["judge_keeps"] = not ch
            sh["changed"], sh["keeps"] = ch, sh["judge_keeps"]
        camera_backstop(rec["verdict"], teardown_p.read_text(), brief)
        rec["findings"] = number(rec["verdict"])
    ok = approved()
    open_ = [f for f in rec["findings"] if not (ok == "all" or f["n"] in ok)]
    rec["approved"] = [f["n"] for f in rec["findings"] if f not in open_]
    rec["passed"] = not open_
    rec_p.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")

    note = d / "SWIPE-MATCH.md"
    if open_:
        note.write_text(
            "# The brief does not keep the swipe's structure\n\n"
            "Production will refuse this brief until each change below is fixed, or the owner "
            "approves it by number (`--approve-structure M1,M2` or `all`).\n\n"
            "| # | Swipe shot | Brief scenes | The swipe has | The brief has | What changed |\n"
            "|---|---|---|---|---|---|\n"
            + "".join(f"| {f['n']} | {f['swipe']} | {', '.join(f['brief_scenes'])} | {f['swipe_has']} | "
                      f"{f['brief_has']} | {'; '.join(f['changed'])} |\n" for f in open_))
    elif note.exists():
        note.unlink()
    label = ("PASSED" + (f" (approved by the owner: {', '.join(rec['approved'])})" if rec["approved"] else "")
             if not open_ else f"HELD — {len(open_)} change(s) from the swipe, see SWIPE-MATCH.md")
    old_read = READ.search(brief)
    keep = old_read.group(0) if old_read and old_read.group(0).rstrip().endswith(f"· {h} -->") else ""
    blk = MANIFEST_BLOCK.search(brief)
    brief_p.write_text(f"<!-- swipe-match: {label} · {h} -->\n" + keep + unstamped(brief).rstrip() + ("\n\n" + blk.group(0).strip() + "\n" if blk else "\n"))
    return not open_, open_


def approve_read(brief_path, by="the owner"):
    """DAMON READS THE BRIEF (2026-09-24: "i always need to see a written brief
    before moving on to the production stage … so I can actually read the
    script before it goes out"). Written only when he says he has read it and
    it can go; tied to the brief's fingerprint, so an edit after his read
    needs his read again."""
    p = Path(brief_path)
    text = p.read_text()
    h = brief_hash(text)
    m = STAMP.search(text)
    sm = m.group(0) if m else ""
    import time
    blk = MANIFEST_BLOCK.search(text)
    p.write_text(sm + f"<!-- brief-read: APPROVED by {by} {time.strftime('%Y-%m-%d %H:%M')} · {h} -->\n" + unstamped(text).rstrip()
                 + ("\n\n" + blk.group(0).strip() + "\n" if blk else "\n"))


def read_of(brief_text):
    """'APPROVED', 'STALE' or None — production refuses anything but APPROVED."""
    m = re.search(r"^<!-- brief-read: APPROVED[^\n]*· ([0-9a-f]{16}) -->", brief_text, re.M)
    if not m:
        return None
    return "APPROVED" if m.group(1) == brief_hash(brief_text) else "STALE"


def stamp_of(brief_text):
    """What production reads: 'PASSED', 'HELD' or None (never checked)."""
    m = re.search(r"^<!-- swipe-match: (PASSED|HELD)[^\n]*· ([0-9a-f]{16}) -->", brief_text, re.M)
    if not m:
        return None
    # A brief edited after its check is not the brief that passed.
    return m.group(1) if m.group(2) == brief_hash(brief_text) else "STALE"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--brief", default="5-brief.md")
    ap.add_argument("--approve-structure", default="")
    ap.add_argument("--damon-read", action="store_true",
                    help="the owner has read this brief and says it can go to production — stamps his read, nothing else")
    a = ap.parse_args()
    if a.damon_read:
        approve_read(Path(a.run_dir) / "stages" / a.brief)
        print("BRIEF READ: approved by the owner"); sys.exit(0)
    if a.approve_structure:
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = a.approve_structure
    passed, open_ = check(a.run_dir, a.brief)
    for f in open_:
        print(f"  {f['n']}  {f['swipe']:<12} {', '.join(f['brief_scenes']):<10} {'; '.join(f['changed'])[:140]}")
    print("SWIPE MATCH:", "PASSED" if passed else f"HELD ({len(open_)})")
    sys.exit(0 if passed else 1)
