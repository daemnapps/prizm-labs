"""Make a person's OWN voice — from a REAL recording, adjusted by a
description, three options for the owner to pick by ear (the owner, 2026-09-23: "we
need to create a voice just for our person … not June's"; "ALL elements in
this flow must be processed from a real reference"; "every element
documented").

    python3 make_voice.py options <person-folder> --line "a line from the brief" [--out DIR] [--dry-run]
    python3 make_voice.py pick    <person-folder> --option N [--out DIR]
    python3 make_voice.py remix   <person-folder> --change "what to fix" [--line ...]

The person's `spec.json` carries the voice recipe:

    "voice": {"persona": "who they sound like, after the adjustments",
              "adjustments": ["what changes from the real speaker"],
              "real_reference": {"file": "reference/voice-*.mp3", "kind": "real audio",
                                 "from": "where the recording came from"}}

`options` REFUSES without a real recording or without adjustments, then asks
ElevenLabs Voice Design (v3, the recording as `reference_audio_base64`, the
persona + adjustments as the description) for three previews reading the same
brief line, and writes option-1..3.mp3 + request.json into --out (default
`<person>/voice/` — the voice lives with the person in runs/ai-elements/<brand>/casting). Nothing
is saved to the account yet.

`pick` saves the chosen preview as a permanent voice on our account and writes
`voice.json` into the person's folder and `voice-provenance.json` beside the
options in `voice/`.

Endpoints and model ids come from `providers.json → direct.elevenlabs_design`
when present, else the documented defaults below.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next((d for d in HERE.parents
           if (d / "components").is_dir() and (d / "brands").is_dir()), HERE.parents[2])
DESIGN = "https://api.elevenlabs.io/v1/text-to-voice/design"
REMIX = "https://api.elevenlabs.io/v1/text-to-voice/{voice_id}/remix"
# every request asks for a clean recording and states who is speaking first
# (the owner, 2026-09-23: "the audio is muffled… option 2 and 3 are literally men")
CLEAN = "Recorded clean: crisp, close-mic, studio quality — no muffling, no room echo, no background noise."
SAVE = "https://api.elevenlabs.io/v1/text-to-voice"
MODEL = "eleven_ttv_v3"            # the only design model that takes a reference recording
REAL_KINDS = ("real audio", "real video frame")


def _voice_mod():
    import importlib.util as ilu
    sp = ilu.spec_from_file_location("vm_voice", HERE / "voice.py")
    m = ilu.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def _post(url: str, body: dict, key: str) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"ElevenLabs {e.code}: {e.read().decode()[:400]}")
        except (TimeoutError, urllib.error.URLError):
            if i == 3:
                raise
            time.sleep(6 * (i + 1))


def recipe(person: Path) -> tuple[dict, dict, list[str]]:
    spec = json.loads((person / "spec.json").read_text())
    v = spec.get("voice") or {}
    gaps = []
    ref = v.get("real_reference") or {}
    if not ref.get("file") or not (person / ref["file"]).is_file():
        gaps.append("no real recording — a voice starts from real audio of a real speaker (voice.real_reference.file)")
    elif ref.get("kind") != "real audio":
        gaps.append(f"voice reference kind `{ref.get('kind')}` is not `real audio`")
    if not ref.get("from"):
        gaps.append("the recording has no `from` — where it came from must be recorded")
    if not v.get("adjustments"):
        gaps.append("no adjustments — the voice is built from a real speaker and made our own, never a copy")
    if not (v.get("persona") or (spec.get("character") or {}).get("voice")):
        gaps.append("no persona")
    gaps += borrowed_voice(person, v)
    return spec, v, gaps


def borrowed_voice(person: Path, v: dict) -> list[str]:
    """ONE REAL SPEAKER, ONE CHARACTER (the owner, 2026-09-23: "you're literally
    using wrong voices for different people… the counter woman has voices from
    the doctors"). A character's real recording may not be the same audio — or
    the same source segment — as another character's, unless the spec says
    `derived_from: <that character>` (e.g. a grandmother built as an older version of a banked person, on purpose)."""
    import hashlib
    ref = v.get("real_reference") or {}
    f = person / ref.get("file", "")
    if not f.is_file():
        return []
    mine = hashlib.sha256(f.read_bytes()).hexdigest()
    src = (ref.get("from") or "").split(" (")[0] + "|" + "".join(ch for ch in (ref.get("from") or "") if ch.isdigit())[-12:]
    out = []
    for other in sorted(person.parent.iterdir()):
        if other == person or other.name.startswith("_") or not (other / "spec.json").is_file():
            continue
        ov = (json.loads((other / "spec.json").read_text()).get("voice") or {})
        oref = ov.get("real_reference") or {}
        of = other / oref.get("file", "")
        same = of.is_file() and hashlib.sha256(of.read_bytes()).hexdigest() == mine
        osrc = (oref.get("from") or "").split(" (")[0] + "|" + "".join(ch for ch in (oref.get("from") or "") if ch.isdigit())[-12:]
        if (same or (oref.get("from") and osrc == src)) and v.get("derived_from") != other.name and ov.get("derived_from") != person.name:
            out.append(f"this voice's real recording is also {other.name}'s — every character gets their own real speaker (or say derived_from: {other.name})")
    return out


def refuse_brands(person, ws: Path | None = None) -> None:
    """A person lives in runs/ai-elements/<brand>/casting/<person>/ — never
    under brands/ (2026-10-08). Refused before any read or request."""
    brands = (Path(ws) if ws else WS).resolve() / "brands"
    if Path(person).resolve().is_relative_to(brands.resolve()):
        raise SystemExit(f"REFUSED: {person} is under brands/ — a person lives in "
                         f"runs/ai-elements/<brand>/casting/<person>/ (element_paths.casting_root)")


def options(person: Path, line: str, out: Path | None = None, dry_run: bool = False) -> Path:
    refuse_brands(person)
    spec, v, gaps = recipe(person)
    if gaps:
        raise SystemExit("REFUSED — " + "\n  ".join([""] + gaps))
    out = out or person / "voice"
    out.mkdir(parents=True, exist_ok=True)
    _archive_round(out)
    persona = v.get("persona") or spec["character"]["voice"]
    who = v.get("gender") or ""
    desc = (f"A {who}. " if who else "") + persona + " Changes from the reference speaker: " + "; ".join(v["adjustments"]) + ". " + CLEAN
    text = line if len(line) >= 100 else (line + " " + line)[:1000]
    audio = (person / v["real_reference"]["file"]).read_bytes()
    body = {"voice_description": desc[:1000], "model_id": MODEL, "text": text[:1000],
            "reference_audio_base64": base64.b64encode(audio).decode(),
            "prompt_strength": v.get("prompt_strength", 0.5), "guidance_scale": 5, "seed": 1}
    shown = {**body, "reference_audio_base64": f"<{len(audio)} bytes of {v['real_reference']['file']}>"}
    (out / "request.json").write_text(json.dumps(shown, indent=1))
    if dry_run:
        print(json.dumps(shown, indent=1)); return out
    key = _voice_mod().key_of()
    if not key:
        raise SystemExit("no ELEVENLABS_API_KEY in the environment or the Keychain")
    data = _post(DESIGN, body, key)
    rows = []
    for i, p in enumerate(data.get("previews") or [], 1):
        (out / f"option-{i}.mp3").write_bytes(base64.b64decode(p["audio_base_64"]))
        rows.append({"option": i, "file": f"option-{i}.mp3", "generated_voice_id": p["generated_voice_id"],
                     "seconds": p.get("duration_secs")})
    (out / "options.json").write_text(json.dumps({"person": spec["id"], "text": data.get("text") or text,
                                                  "description": desc, "options": rows,
                                                  "made": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1))
    print(f"{len(rows)} options → {out}")
    _qc(person)
    return out


def _helpers_python(ws: Path) -> Path:
    """The helpers venv's interpreter — video-edit's, at its components home."""
    return ws / "tools" / "video-edit" / ".venv" / "bin" / "python"


def _qc(person: Path) -> None:
    """Run voice_qc.py in the helpers venv (librosa) so every round is measured
    before anyone listens; skipped with a note when the venv is not there."""
    import subprocess
    ws = _voice_mod().WORKSPACE
    py = _helpers_python(ws)
    if not py.exists():
        print("  voice check skipped — no helpers venv (tools/video-edit/.venv)"); return
    r = subprocess.run([str(py), str(HERE / "voice_qc.py"), str(person)], capture_output=True, text=True, cwd="/")
    print(r.stdout.strip() or r.stderr.strip()[-300:])


def _archive_round(out: Path) -> None:
    """A new round of options never overwrites the last one — it moves to
    voice/versions/round-N/, so every option ever heard is kept."""
    if not (out / "options.json").is_file():
        return
    n = 1
    while (out / "versions" / f"round-{n}").exists():
        n += 1
    dst = out / "versions" / f"round-{n}"; dst.mkdir(parents=True)
    for f in list(out.glob("option-*.mp3")) + [out / "options.json", out / "request.json", out / "check.json"]:
        if f.is_file():
            f.rename(dst / f.name)


def remix(person: Path, change: str, line: str | None = None, out: Path | None = None, base: Path | None = None) -> Path:
    """Three new previews of the voice already picked, changed only as asked
    (e.g. "clean up the muffled audio") — the person stays the same person."""
    refuse_brands(person)
    if base:
        refuse_brands(base)
    spec, v, _ = recipe(person)
    # base: another person's picked voice to build from (the owner, 2026-09-23: "for
    # the elder, use the latest approved voice … make her sound like an 80 year old")
    vj = json.loads(((base or person) / "voice.json").read_text())
    out = out or person / "voice"
    _archive_round(out)
    who = v.get("gender") or ""
    desc = ((f"Keep the same {who or 'person'} and the same voice. ") if not base else "") + change + " " + CLEAN
    text = line or json.loads((out / "versions").glob("round-*/options.json").__next__().read_text()).get("text", "")
    body = {"voice_description": desc[:1000], "text": text[:1000], "guidance_scale": 2, "seed": 1}
    (out / "request.json").write_text(json.dumps({**body, "remix_of": vj["voice_id"]}, indent=1))
    data = _post(REMIX.format(voice_id=vj["voice_id"]), body, _voice_mod().key_of())
    rows = []
    for i, p in enumerate(data.get("previews") or [], 1):
        (out / f"option-{i}.mp3").write_bytes(base64.b64decode(p["audio_base_64"]))
        rows.append({"option": i, "file": f"option-{i}.mp3", "generated_voice_id": p["generated_voice_id"], "seconds": p.get("duration_secs")})
    (out / "options.json").write_text(json.dumps({"person": spec["id"], "text": data.get("text") or text, "description": desc,
                                                  "remix_of": vj["voice_id"], "remix_of_person": (base or person).name, "options": rows, "made": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1))
    print(f"{len(rows)} remix options → {out}")
    _qc(person)
    return out


def pick(person: Path, n: int, out: Path | None = None, by: str = "the owner by ear") -> dict:
    refuse_brands(person)
    spec, v, gaps = recipe(person)
    out = out or person / "voice"
    opts = json.loads((out / "options.json").read_text())
    row = next(r for r in opts["options"] if r["option"] == n)
    key = _voice_mod().key_of()
    saved = _post(SAVE, {"voice_name": f"{spec['character']['title'].split(' — ')[0]} — {spec['brand']}",
                         "voice_description": opts["description"][:1000],
                         "generated_voice_id": row["generated_voice_id"]}, key)
    vj = {"voice_id": saved["voice_id"], "name": f"{spec['id']} — {spec['brand']}",
          "model_id": "eleven_v3",
          "settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": False, "speed": 1.0},
          "source": f"designed {time.strftime('%Y-%m-%d')} with make_voice.py from a real recording + adjustments; option {n} of {len(opts['options'])}, picked by {by}"}
    (person / "voice.json").write_text(json.dumps(vj, indent=1))
    (out / "voice-provenance.json").write_text(json.dumps({
        "element": f"{spec['id']}-voice", "kind": "voice", "real_references": [v["real_reference"]],
        "adjustments": v["adjustments"], "description_sent": opts["description"],
        "made_with": {"endpoint": DESIGN, "model": MODEL, "tool": "tools/video-production/machine/make_voice.py"},
        "picked": n, "options": opts["options"], "voice_id": saved["voice_id"],
        "rights": spec.get("rights") or ""}, indent=1))
    print(json.dumps(vj, indent=1))
    return vj


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("options"); o.add_argument("person"); o.add_argument("--line", required=True)
    o.add_argument("--out"); o.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("pick"); p.add_argument("person"); p.add_argument("--option", type=int, required=True); p.add_argument("--out")
    p.add_argument("--by", default="the owner by ear", help="who picked it — only the owner's own pick says 'the owner by ear'")
    r = sub.add_parser("remix"); r.add_argument("person"); r.add_argument("--change", required=True); r.add_argument("--line")
    r.add_argument("--from", dest="base", help="build from another person's picked voice (their folder)")
    a = ap.parse_args(argv)
    if a.cmd == "options":
        options(Path(a.person).resolve(), a.line, Path(a.out) if a.out else None, a.dry_run)
    elif a.cmd == "remix":
        remix(Path(a.person).resolve(), a.change, a.line, base=Path(a.base).resolve() if a.base else None)
    else:
        pick(Path(a.person).resolve(), a.option, Path(a.out) if a.out else None, a.by)
    return 0


if __name__ == "__main__":
    sys.exit(main())
