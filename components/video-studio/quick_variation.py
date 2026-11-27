"""Quick variation: a finished production -> a new production with some lines swapped (an angle, a word, an offer line),
the same scenes, shots, cards, layout and hooks. No writing chain: the lines given are the only change.

  python3 quick_variation.py <production> <new production> --lines lines.json [--title "..."] [--key <ledger key>]
                            [--face <sex/age band/ethnicity>]

--face recasts the copy for another demographic (e.g. male/25-34/black): it is written as brief.json `audience.face`, and
every voice is set again from the brand's voice list (voices.py, rule 2026-11-12): the narrator for that face, each take's
on-camera speaker for its own face (lines.json "cast_faces": {"HOST": "male/25-34/black", "RATER": "female/25-34/black"}).
A face with no voice set is refused before anything is copied. The people on screen are recast by the usual line
(shot_fill with the new person, cast sheets, prints); the copy says what still shows the old cast (`recast`).

lines.json: {"why": "the owner's words", "lines": {"S6": "fading the dark spots on your arms,", ...},
             "sent": {"S6": "what the voice reads, when it differs from the caption spelling"},
             "hooks": {"H2": "a new opening line", ...},     a hook not named keeps its line
             "cast_faces": {"HOST": "male/25-34/black", ...}}  with --face: each take's speaker's own demographic
Copies brief.json (number, title, key, `variation_of`), every picked take (as take-1, its read back to `voice.ai` so the
Studio's Next step reads the new script), scene cards, picks.json, shot-list.json and voice/reads.json with the new
lines. Hook reads are made again for every hook (its words may change). Then the Studio's Next step runs as usual:
Read the narration -> Cut to the swipe -> Check -> Render (cut + hooks). Brand-agnostic.
"""
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402


def load(p):
    return json.load(open(p))


def save(p, d):
    json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)


def make(src, new, spec, title=None, key=None, face=None):
    A, B = ST.BRIEFS / src, ST.BRIEFS / new
    if B.exists():
        raise SystemExit("%s exists: a variation is made once" % new)
    brief = load(A / "brief.json")
    import voices as VO
    if face:                             # every voice of the new face is set before anything is copied (rule 2026-11-12)
        face = VO.norm_face(face)
        if not face:
            raise SystemExit("--face reads <sex>/<age band>/<ethnicity>, e.g. male/25-34/black")
        VO.voice_for(VO.brand_of(brief), face)
        for name, f in (spec.get("cast_faces") or {}).items():
            VO.voice_for(VO.brand_of(brief), f, name)
    lines, sent, hooks = spec.get("lines") or {}, spec.get("sent") or {}, spec.get("hooks") or {}
    unknown = [s for s in list(lines) + list(sent) if s not in brief["order"]] + [h for h in hooks if h not in (brief.get("hooks") or [])]
    if unknown:
        raise SystemExit("not in %s: %s" % (src, ", ".join(unknown)))
    B.mkdir(parents=True)
    reads = load(A / "voice" / "reads.json")
    for s, t in list(lines.items()) + list(hooks.items()):
        reads["lines"][s] = {"text": t, "sent": sent.get(s, t)}
    for s in sent:
        reads["lines"][s]["sent"] = sent[s]
    (B / "voice").mkdir()
    reads["note"] = "Quick variation of %s (%s)." % (src, spec.get("why") or "")
    save(B / "voice" / "reads.json", reads)
    picks = {}
    for s in brief["order"] + list(brief.get("hooks") or []):
        wf = load(A / "scenes" / s / (brief["picks"][s] + ".json"))
        d = B / "scenes" / s
        d.mkdir(parents=True)
        if (A / "scenes" / s / "card").is_dir():
            shutil.copytree(A / "scenes" / s / "card", d / "card", ignore=shutil.ignore_patterns("index.html", "bg.mp4"))
        text = reads["lines"].get(s, {}).get("text", wf.get("words"))
        steps = []
        for st in wf["steps"]:
            if st["tool"] == "voice.read" and s in brief["order"]:     # the body is read again, as one continuous read
                st = {"id": "voice", "tool": "voice.ai", "model": None, "prompt": text, "seed": None, "inputs": {},
                      "params": {"speaker": st["params"].get("speaker", "NARRATOR")}, "note": "quick variation line"}
            elif st["tool"] == "voice.read":                              # a hook keeps its own read file, made below
                st = dict(st, prompt=text, inputs={"file": "voice/hooks/%s.mp3" % s})
            steps.append(st)
        save(d / "take-1.json", dict(wf, take="take-1", words=text, steps=steps,
                                     **{"from": "quick variation of %s/%s %s" % (src, s, brief["picks"][s])}))
        picks[s] = "take-1"
    for f in ("picks.json", "shot-list.json", "SHOT-LIST.md", "shot-fill.json", "SHOT-FILL.md"):
        if (A / f).exists():
            shutil.copy(A / f, B / f)
    brief.update(number=new, picks=picks, variation_of=src, variation_why=spec.get("why"),
                 title=title or "%s · variation" % brief.get("title", src))
    if key:                              # the copy's own ledger key; `brief` stays the writing run the tools look up
        brief["brief_key"] = key
        brief.setdefault("run", brief.get("brief"))
    if brief.get("idea"):                # one production per storyboard idea: the copy is its own ad in the menu
        brief["from_idea"] = brief.pop("idea")
    if face:
        brief["audience"] = dict(brief.get("audience") or {}, face=face)
        brief["recast"] = ("the people on screen still show %s's cast: re-pick the body (shot_fill with the new person), "
                           "recast every take's cast sheets and reprint its start picture" % src)
    save(B / "brief.json", brief)
    if face:
        VO.apply(new, spec.get("cast_faces"))
        reads = load(B / "voice" / "reads.json")
    spoken = [h for h in (brief.get("hooks") or []) if h in reads["lines"]]   # a hook that is a whole take speaks itself
    if brief.get("hooks"):                                                 # hook reads, in the production's voice
        import voice_continuous as VC
        (B / "voice" / "hooks").mkdir(exist_ok=True)
        for h in spoken:
            mp3 = B / "voice" / "hooks" / ("%s.mp3" % h)
            VC.tts(reads["lines"][h]["sent"], reads["voice_id"], 1, str(mp3), reads.get("model") or "eleven_v3", reads.get("settings"))
            save(B / "voice" / "hooks" / ("%s.words.json" % h), {"scene": h, "words": VC.stt(str(mp3))})
        import urllib.request                                              # hook openers are made now: the render
        studio = os.environ.get("VIDEO_STUDIO_URL", "http://127.0.0.1:8922")   # step only renders scenes already made
        for h in ([] if face else brief["hooks"]):                         # a recast copy makes its hooks once recast
            r = urllib.request.Request("%s/api/scene/%s/%s/run" % (studio, new, h), data=b"{}",
                                       headers={"Content-Type": "application/json"}, method="POST")
            ok = json.loads(urllib.request.urlopen(r, timeout=900).read()).get("ok")
            if not ok:
                raise SystemExit("hook %s was not made: run it in the Studio before rendering" % h)
    print(json.dumps({"production": new, "variation_of": src, "lines": len(lines), "hooks": len(brief.get("hooks") or []),
                      **({"face": face, "voices": VO.report(new), "recast": brief["recast"]} if face else {}),
                      "next": "recast the people, then Studio Next step" if face else "Studio Next step: Read the narration"},
                     ensure_ascii=False, default=str))


if __name__ == "__main__":
    a = sys.argv[1:]
    spec = load(a[a.index("--lines") + 1])
    make(a[0], a[1], spec, a[a.index("--title") + 1] if "--title" in a else None, a[a.index("--key") + 1] if "--key" in a else None,
         a[a.index("--face") + 1] if "--face" in a else None)
