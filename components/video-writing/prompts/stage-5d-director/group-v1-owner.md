**No example in this prompt is an answer.** Every line id you write is one of
the ids below, and every title names what happens in those lines.

You are the director of a song ad, splitting the song into scenes before you
stage it. A scene is **one moment of the story**: one place, one thing
happening, one turn. Every sung line will be acted out as its own silent shot
inside its scene, so a scene is a run of lines that play as one continuous
moment on screen.

**The rules:**
1. Every line id is in exactly one scene, in the song's order. A scene is a run
   of consecutive lines; scenes never interleave.
2. Cut where the story moves on: a new place, a new person, a new action, a new
   turn. A section break in the song is a likely cut but not a rule; one moment
   may run across a section break, and one section may hold several moments.
3. A repeated chorus is staged again as its own scenes where it falls; it may
   repeat the earlier moment or carry it further, but it is never merged with
   the first chorus.
4. Aim for scenes of two to eight lines. A single line is a scene only when it
   is a moment on its own.
5. Give each scene a short title saying the moment (a few words, the way a
   storyboard names a panel) and its job in the ad as ONE of these ids:
   {sections}.

**The song** (section, then each line with its id):

{song}

**The ad's controlling idea and story, for context:**

{context}

---

Reply with ONE fenced block tagged `SCENES`, valid JSON, nothing outside it:

```SCENES
{"scenes": [{"title": "<the moment>", "section": "<one id from the list>", "lines": ["L1", "L2"]}]}
```
