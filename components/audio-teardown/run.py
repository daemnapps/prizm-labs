#!/usr/bin/env python3
"""audio-teardown — a video in, the Sound Sheet out.

    python3 run.py <video> --out <dir>

Steps built so far (2026-09-25):
    split      voices lifted off the music (Demucs, on this Mac)
    words      Gemini writes every word, in the language it was said
    speakers   Scribe v2 says who spoke and when
    lines      merged into numbered lines T1…, every disagreement flagged
    voices     one card per person: their own clip, measured (Praat) and heard (Gemini)
    music      named (Shazam, AudD), measured (tempo, key, energy — librosa), heard from the music alone
    effects    every sharp sound timed (onsets + AudioSet tagger), named by an ear, filed under UCS
    mix        loudness, voice over music, ducking, silences, the spoken / music form

Writes into --out (the caller's folder — nothing is written anywhere else):
    audio/voices.mp3, audio/music.mp3, audio/mix.mp3   the split tracks (music.mp3 only when
                     Demucs split them — the sheet's split section says why not)
    words.json       Gemini's answer, as given
    speakers.json    Scribe's answer, as given
    transcript.json  the lines — the shape the video chain already reads, plus language and flags
    transcript.md    the same, for a person
    voices/voice-<n>.mp3, voices/voice-cards.json   one clip and one card per person
    sound-sheet.json what is filled of the Sound Sheet so far (languages, voices, models, flags)
    sound-sheet.md   the transcript and the voice cards, for a person

Brand-agnostic: it reads only the video. Voices, music, effects and the mix come
in later steps; their fields stay absent until then, never guessed.
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lines as L          # noqa: E402
import speakers as SP      # noqa: E402
import split as SPL        # noqa: E402
import voices as V         # noqa: E402
import music as MU         # noqa: E402
import effects as EF       # noqa: E402
import mix as MX           # noqa: E402
import words as W          # noqa: E402


def stamp(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def render(lines, langs):
    md = ["### VERBATIM TRANSCRIPT", "",
          "Every word of the swipe, in the language it was spoken, transcribed from its audio (not a model's summary). "
          "One line per speaker turn, numbered. Languages: "
          + ", ".join(f"{k} {v}%" for k, v in langs.items()) + ".", "",
          "| # | Time | Speaker | Lang | Line (verbatim) |", "|---|---|---|---|---|"]
    for l in lines:
        flag = f" ⚑ {', '.join(l['flags'])}" if l["flags"] else ""
        md.append(f"| {l['id']} | {stamp(l['start'])} | {l['speaker']} | {l['language']} | "
                  f"{l['text'].replace('|', '/')}{flag} |")
    return "\n".join(md) + "\n"


def teardown(video, out, reuse=False):
    """reuse: keep the words, speakers and voice cards already in --out and add
    only what is missing (music, effects, mix) — for runs made before those existed."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    tracks = SPL.split(Path(video), out / "audio")
    total = SPL.duration(tracks["mix"])
    if reuse and (out / "transcript.json").exists() and (out / "sound-sheet.json").exists():
        return add_sound(video, out, tracks, t0)
    with ThreadPoolExecutor(2) as ex:                  # the two listeners, at the same time
        fw = ex.submit(W.listen, tracks["voices"])
        fs = ex.submit(SP.listen, tracks["voices"])
        try:
            words = fw.result()
        except Exception as e:
            words = {"model": None, "error": str(e)[:300], "lines": []}
        scribe = fs.result()
    (out / "words.json").write_text(json.dumps(words, indent=1, ensure_ascii=False) + "\n")
    (out / "speakers.json").write_text(json.dumps(scribe, indent=1, ensure_ascii=False) + "\n")
    if words.get("model"):
        lines = L.merge(words["lines"], scribe["words"], scribe.get("language"), total)
    else:
        lines = L.from_scribe_only(scribe["words"], scribe.get("language"))
    langs = L.languages(lines)
    (out / "transcript.json").write_text(json.dumps(lines, indent=1, ensure_ascii=False) + "\n")
    (out / "transcript.md").write_text(render(lines, langs))
    sheet = {
        "video": str(video), "seconds": round(total, 1),
        "split": {"how": tracks["how"], "why": tracks["why"],      # music.mp3 is written only when how is demucs
                  "music": "audio/music.mp3" if tracks["music"] else "not written — " + tracks["why"]},
        "words": {"model": words.get("model"), "prompt": words.get("prompt"), "fell_back": words.get("tried") or [],
                  "error": words.get("error")},
        "speakers": {"model": scribe["model"], "scribe_language": scribe.get("language")},
        "languages": langs,
        "switches_language": len([k for k in langs if k != "?"]) > 1,
        "voices": len({l["speaker"] for l in lines}),
        "lines": len(lines),
        "flags": {f: sum(f in l["flags"] for l in lines) for f in
                  ("scribe-dropped", "scribe-translated", "heard-differently", "speaker-from-words-model", "scribe-only")},
        "took_seconds": round(time.time() - t0, 1),
    }
    cards = V.cards(lines, tracks["voices"], out / "voices", total)   # no lines: voice-cards.json with no cards
    sheet["voice_cards"] = [{k: c.get(k) for k in ("speaker", "languages", "accent", "age_band", "gender_presentation",
                                                  "read_style", "delivery_style", "casting_call", "voice_prompt",
                                                  "unknown_labels", "heard_error")} | {"measured": c.get("measured")}
                            for c in cards]
    (out / "sound-sheet.json").write_text(json.dumps(sheet, indent=1, ensure_ascii=False) + "\n")
    return add_sound(video, out, tracks, t0)


def add_sound(video, out, tracks, t0):
    """Music, effects and the mix, added to the sheet the words and voices made."""
    sheet = json.loads((out / "sound-sheet.json").read_text())
    lines = json.loads((out / "transcript.json").read_text())
    vc = out / "voices" / "voice-cards.json"
    cards = json.loads(vc.read_text())["cards"] if vc.exists() else []
    with ThreadPoolExecutor(2) as ex:                  # music and effects listen at the same time
        fm = ex.submit(MU.read, tracks.get("music"))
        mu = fm.result()
        fe = ex.submit(EF.read, tracks.get("music"), (mu.get("measured") or {}).get("beats"))
        ef = fe.result()
    mx = MX.read(video, tracks, lines, mu)
    sheet["music"] = {k: v for k, v in mu.items()}
    if sheet["music"].get("measured"):
        sheet["music"]["measured"] = {k: v for k, v in mu["measured"].items() if k != "downbeats_guess"}
    sheet["effects"] = {k: v for k, v in ef.items() if k != "machine"} | {"machine_candidates": len(ef.get("machine", {}).get("candidates", []))}
    sheet["mix"] = mx
    sheet["took_seconds"] = round(time.time() - t0, 1)
    (out / "effects-machine.json").write_text(json.dumps(ef.get("machine", {}), indent=1) + "\n")
    (out / "sound-sheet.json").write_text(json.dumps(sheet, indent=1, ensure_ascii=False) + "\n")
    langs = sheet.get("languages") or L.languages(lines)
    (out / "sound-sheet.md").write_text("\n".join([render(lines, langs), V.render(cards), MU.render(mu),
                                                   EF.render(ef), MX.render(mx)]))
    return sheet


def main():
    ap = argparse.ArgumentParser(description="A video in, the Sound Sheet out: words in every language, voices, music, effects, mix.")
    ap.add_argument("video")
    ap.add_argument("--out", required=True, help="the caller's folder; everything is written under it")
    ap.add_argument("--reuse", action="store_true",
                    help="keep the words and voice cards already in --out; add only music, effects and the mix")
    a = ap.parse_args()
    s = teardown(a.video, a.out, reuse=a.reuse)
    print(f"{s['lines']} lines · {s['voices']} voices · languages {s['languages']} · words by {s['words']['model']} "
          f"· split {s['split']['how']} · {s['took_seconds']}s")
    mu, fx = s.get("music") or {}, (s.get("effects") or {}).get("effects") or []
    song = (mu.get("song") or {})
    print(f"music: {'none' if not mu.get('present') else (song.get('title') or 'unnamed') + ' · ' + str((mu.get('measured') or {}).get('tempo_bpm')) + ' bpm · ' + str((mu.get('measured') or {}).get('key'))}"
          f" · effects: {len(fx)} · loudness {((s.get('mix') or {}).get('loudness') or {}).get('lufs')} LUFS")
    bad = {k: v for k, v in s["flags"].items() if v}
    if bad:
        print("flags: " + ", ".join(f"{k} {v}" for k, v in bad.items()))


if __name__ == "__main__":
    main()
