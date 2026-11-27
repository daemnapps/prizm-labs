"""Voices: every speaking role in a video takes the one voice set for its demographic (rule 2026-11-12: every voice in an
ad matches the demographic on screen; one voice per demographic, set once, never picked per ad).

The list is brands/<brand>/ai-elements/voices.json: {"voices": {"<sex>/<age band>/<ethnicity>": {"voice_id", "name",
"model", "settings"}}}. The narrator takes the row of the people on screen (the production's face); each on-camera
speaker takes the row of their own face (a take's cast member `face`).

    python3 voices.py <production>            what each speaking role reads in, and what does not match
    python3 voices.py <production> --apply    write the matching voices into voice/reads.json and every take's cast

Where a production's face comes from, in order: brief.json `audience.face`; the brief record's `moves.face`
(brands/<brand>/briefs/briefs.json, by brief_key); brief.json `shot_fill.person` (a library path ".../male/black/25-34/...").
A face with no row is refused by name: choose one real voiceprint of that demographic and add its row. Brand-agnostic.
THE RULE is the chain's (components/video-production/machine/voice_cast.py), called from here, never copied (owner
ruling 2026-11-16, V57 (swipe is the backbone)); this file reads and writes the Studio's production files.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

VC = ST.chain("video-production", "voice_cast")     # one voice per demographic: the chain's rule
ETHNIC = VC.ETHNIC
NoVoice = VC.NoVoice
norm_face = VC.norm_face


def load(p):
    return json.load(open(p))


def brand_of(brief):
    key = str(brief.get("brief_key") or brief.get("brief") or "")
    return key.split("_", 1)[0] if "_" in key else key.split("-", 1)[0]


def registry(brand):
    return VC.registry(brand, ST.REPO)


def face_of(brief):
    """The production's on-screen demographic, or None when nothing says it."""
    f = (brief.get("audience") or {}).get("face")
    if f:
        return norm_face(f)
    brand = brand_of(brief)
    rec = ST.REPO / "brands" / brand / "briefs" / "briefs.json"
    key = str(brief.get("brief_key") or "")
    m = re.search(r"brief-\d{4}", key)
    if rec.is_file() and m:
        rows = load(rec).get("briefs") or []
        rows = rows if isinstance(rows, list) else list(rows.values())
        row = next((r for r in rows if r.get("brief") == m.group(0)), None)
        if row and (row.get("moves") or {}).get("face"):
            return norm_face(row["moves"]["face"])
    person = norm_face((brief.get("shot_fill") or {}).get("person"))
    if person:
        return person
    # nobody named on camera: the footage's demographic sets the voice (the folder the shot match draws from, e.g.
    # /female/white/45-54/), never the brand's last ad's voice (20 Nov: four ads came out in another woman's voice)
    hl = ((brief.get("shot_fill") or {}).get("hands_like") or [None])[0]
    m2 = re.search(r"/(female|male)/([a-z-]+)/(\d\d-\d\d)/", str(hl or ""))
    return norm_face("%s/%s/%s" % (m2.group(1), m2.group(3), m2.group(2))) if m2 else None


def voice_for(brand, face, role="the narrator"):
    return VC.voice_for(brand, face, role, rows=registry(brand))


def _takes(n, brief):
    B = ST.BRIEFS / n
    for s in list(brief.get("order") or []) + list(brief.get("hooks") or []):
        p = B / "scenes" / s / (brief["picks"][s] + ".json")
        if p.is_file():
            yield s, p


def report(n):
    """{role: {face, wants, has, ok}} for the narrator and every on-camera speaker with a face."""
    B = ST.BRIEFS / n
    brief = load(B / "brief.json")
    brand, out = brand_of(brief), {}
    face = face_of(brief)
    rf = B / "voice" / "reads.json"
    # A CHAIN-MADE AD READS IN ITS SPEAKER'S OWN BANKED VOICE (owner, 2026-11-20: a character speaks in their own saved
    # voice, never the demographic set; 2026-11-21, brief-0380: the check wanted a stock voice for Yai's reads)
    own = None
    if (brief.get("lane") or "") == "ai":
        try:
            import chain_view as CV
            own = CV.speaker_voice(brief)
        except Exception:  # noqa: BLE001 -- no chain voice read: the demographic set decides, as before
            own = None
    if own and rf.is_file():
        has = load(rf).get("voice_id")
        out["narrator"] = {"face": own.get("voice") or face, "wants": own["voice_id"], "has": has,
                           "ok": has == own["voice_id"], "from": own.get("from")}
    elif face and rf.is_file():
        has = load(rf).get("voice_id")
        try:
            want = voice_for(brand, face)["voice_id"]
        except NoVoice as e:
            want = None
            out["narrator"] = {"face": face, "wants": None, "has": has, "ok": False, "why": str(e)}
        if want:
            out["narrator"] = {"face": face, "wants": want, "has": has, "ok": has == want}
    for s, p in _takes(n, brief):
        for st in load(p).get("steps") or []:
            if st.get("tool") != "gen.take":
                continue
            for name, c in ((st.get("params") or {}).get("cast") or {}).items():
                if not isinstance(c, dict) or not c.get("face"):
                    continue
                try:
                    want = voice_for(brand, c["face"], f"{s} {name}")["voice_id"]
                except NoVoice:
                    want = None
                spoke = any(ln.get("speaker") == name and ln.get("say") for ln in (st["params"].get("script") or []))
                if spoke:
                    out[f"{s} {name}"] = {"face": norm_face(c["face"]), "wants": want, "has": c.get("voice_id"),
                                          "ok": bool(want) and c.get("voice_id") == want}
    return out


def apply(n, cast_faces=None):
    """Write the matching voices: the narrator into voice/reads.json, each speaker into every take's cast (`face`,
    `voice_id`, `settings`; the old `voice` name is kept as `voice_was`). cast_faces {NAME: face} sets faces first."""
    B = ST.BRIEFS / n
    brief = load(B / "brief.json")
    brand, face, done = brand_of(brief), face_of(brief), []
    rf = B / "voice" / "reads.json"
    nar = brief.get("narrator") or {}
    if nar.get("voice_id") and rf.is_file():       # a narrator assigned on the production wins (owner, 20 Nov)
        v = {"voice_id": nar["voice_id"], "name": nar.get("voice", ""), "model": nar.get("model"), "settings": nar.get("settings")}
        face = face or "assigned"
    if face and rf.is_file():
        v = v if nar.get("voice_id") else voice_for(brand, face)
        r = load(rf)
        if r.get("voice_id") != v["voice_id"]:
            r["voice_was"] = {k: r.get(k) for k in ("voice_id", "voice", "model")}
        r.update(voice_id=v["voice_id"], voice=v.get("name", ""), face=face)
        if v.get("model"):
            r["model"] = v["model"]
        if v.get("settings"):
            r["settings"] = v["settings"]
        json.dump(r, open(rf, "w"), indent=1, ensure_ascii=False)
        done.append(f"narrator {face} -> {v.get('name')}")
    for s, p in _takes(n, brief):
        wf = load(p)
        touched = False
        for st in wf.get("steps") or []:
            if st.get("tool") != "gen.take":
                continue
            for name, c in ((st.get("params") or {}).get("cast") or {}).items():
                if not isinstance(c, dict):
                    continue
                if cast_faces and name in cast_faces:
                    c["face"] = norm_face(cast_faces[name])
                if not c.get("face"):
                    continue
                v = voice_for(brand, c["face"], f"{s} {name}")
                if c.get("voice"):
                    c["voice_was"] = c.pop("voice")
                c.update(voice_id=v["voice_id"], voice_name=v.get("name", ""))
                if v.get("settings"):
                    c["settings"] = v["settings"]
                touched = True
                done.append(f"{s} {name} {c['face']} -> {v.get('name')}")
        if touched:
            json.dump(wf, open(p, "w"), indent=1, ensure_ascii=False)
    return done


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if "--apply" in a:
        print("\n".join(apply(a[0])) or "nothing to set")
    rep = report(a[0])
    for role, r in rep.items():
        print(("ok  " if r["ok"] else "BAD ") + f"{role:16} {r['face']:22} has {r['has']} wants {r['wants']}")
    sys.exit(0 if all(r["ok"] for r in rep.values()) else 1)
