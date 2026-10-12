"""The teardown counts the Sound Sheet's effects, not the keys of its effects section (SI-146, 2026-10-08).

Since audio-teardown wrote `effects` as a SECTION (run.py:133), the teardown said "9 effect(s)" whatever
the sheet held: it counted the section's keys. A brand-a run said 9 where the sheet had 4.
"""
import json, tempfile
from pathlib import Path
import transcript as tr

T = "## Audio\nMusic: none. Room tone and voice only.\n"
MUSIC = {"present": True, "measured": {"music_share_percent": 99, "tempo_bpm": 136}}


def run(effects, music=MUSIC):
    d = Path(tempfile.mkdtemp())
    rec = {"music": music}
    if effects is not None:
        rec["effects"] = effects
    (d / "sound-sheet.json").write_text(json.dumps(rec))
    return tr.correct_music(T, d)


def line(t):
    return next(l for l in t.splitlines() if l.startswith("Music:"))


fx = [{"t": i, "name": n} for i, n in enumerate(["whoosh", "click", "pop", "ding"])]

# 1. a section of 9 keys holding 4 effects → 4, not 9
section = {"effects": fx, "present": True, "count_onsets": 31, "confirmed": 4, "rejected": 27,
           "categories": ["WHSH", "UI"], "model": "x", "took_seconds": 3.2, "machine_candidates": 31}
assert len(section) == 9, len(section)
out = run(section)
assert "4 effect(s) added in the edit" in line(out), line(out)
assert "9 effect(s)" not in out, out
assert "MEASURED off the audio" in line(out), line(out)
print("OK — section of 9 keys, 4 effects")

# 2. a section with no effects → no effect clause
out = run(dict(section, effects=[]))
assert "effect(s)" not in out, out
assert "MEASURED off the audio" in line(out), line(out)
print("OK — empty section")

# 3. a legacy list-shaped sheet is still counted
out = run(fx[:2])
assert "2 effect(s) added in the edit" in line(out), line(out)
print("OK — legacy list")

# 4. no music → the teardown is untouched
assert run(section, music={"present": False}) == T
print("OK — music absent")
