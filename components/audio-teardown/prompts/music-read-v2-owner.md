*v2 (2026-11-15): heard blind. v1 showed the model the song-recognition answer before it listened; on one swipe Shazam named the wrong song (a sung synth-pop track) and the read described that song instead of the lo-fi R&B guitar beat that was playing, and the music made from the brief came out wrong. The name now stays out of the prompt; a measured tempo can be double or half the felt one, so the felt tempo is asked for too.*

This is ONLY the music track of a short social video: the speech has been removed. Describe it the way a music supervisor briefs a composer, so the same kind of track can be found or made.

What was measured from this track (use it; a beat tracker often reports double or half the tempo a listener feels, so give the felt tempo separately):
{measured}

Describe only what you hear in this audio. You are not told the song's name on purpose: do not guess one and describe it from memory.

Only what you can hear. Mark anything unsure with "(unsure)". Every label field takes values ONLY from these lists; if nothing fits, write "other: <your word>":
{lists}

Return JSON only:
{
 "present": <true if there is music at all>,
 "source": "<music_source value — a known song, a trending platform sound, stock library music, original score>",
 "genre": "<genre>", "subgenre": "<sub-genre>", "era": "<era or reference, e.g. 2010s tropical house>",
 "felt_bpm": <the tempo a listener would nod to, often half or double the measured one>,
 "instruments": ["<what you can hear>"],
 "vocals": "<vocals value>", "vocal_language": "<ISO 639-1 if there are sung or rapped words, else null>",
 "energy": "<energy value>", "valence": "<valence value>", "arousal": "<arousal value>",
 "mood_words": ["<two or three plain words>"],
 "shape": "<shape value — how it moves across the video>",
 "in_scene": "<in_scene value — does it sound like it plays inside the scene (a speaker, a radio, a room) or laid over it>",
 "how_it_sits": "<how it sits under the voice: ducked, loud, gone during speech>",
 "changes": [{"at": <seconds>, "what": "<a drop, a build, a switch, a stop>"}],
 "sounds_like": ["<two real tracks it sounds like, marked (sounds like)>"],
 "composer_brief": "<one paragraph: genre, instruments, feel, tempo, era, how it is built, how it sits under the voice>"
}
