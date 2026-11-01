*v1 (2026-09-30): the music, read from the music alone — the voices have been removed. Three reads of the same swipe once described its music three different ways; quiet music under speech is beyond a model's ear, so this listens to the isolated track, and the tempo, key and energy were already MEASURED by a tool.*

This is ONLY the music track of a short social video: the speech has been removed. Describe it the way a music supervisor briefs a composer, so the same kind of track can be found or made.

What was measured from this track (use it; don't contradict it without saying why):
{measured}

What the song-recognition services said:
{identified}

Only what you can hear. Mark anything unsure with "(unsure)". Every label field takes values ONLY from these lists; if nothing fits, write "other: <your word>":
{lists}

Return JSON only:
{
 "present": <true if there is music at all>,
 "source": "<music_source value — a known song, a trending platform sound, stock library music, original score>",
 "genre": "<genre>", "subgenre": "<sub-genre>", "era": "<era or reference, e.g. 2010s tropical house>",
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
