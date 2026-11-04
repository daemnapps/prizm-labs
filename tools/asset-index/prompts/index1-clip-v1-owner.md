Today is: {today}
Here is where the file sits and what it measures: {file_meta}
Here is what was said in it, transcribed: {transcript}
Here are frames pulled from it, in order, with their timestamps: {frames}

One clip in, one record out. **Observation only** — no judgement about whether
the clip is good, no idea about what it could be cut into, no guess at intent.
That happens when an ad gets built. This stage exists so that every later
search argues against the same record instead of someone re-watching footage
and quietly seeing something different.

You are reading frames, not watching video. Motion between frames is inferred,
never asserted. If two frames differ and you cannot tell what happened between
them, that is a cut or a jump and you say so rather than narrating a movement
you did not see.

**The record is for finding this clip again.** Someone will search it months
from now with a phrase like "guy reacting in a mirror" or "hands applying
product, bathroom light". Every field exists to make that search land. Write
what a person would search for, not what a camera saw.

Give me exactly these fields, as JSON, nothing outside the object:

**`subject`** — who is on screen. Apparent age bracket, apparent gender, hair,
facial hair, notable clothing. Describe appearance only, as casting notes: this
is how a real person gets matched to a role. Never name anyone, never guess at
race or ethnicity, never guess a real identity. If the frame shows only hands
or a body part, say that. If nobody is on screen, `null`.

**`setting`** — where it happens. Room or location, surfaces, lighting quality,
time of day if the frame states it. `unknown` when the background carries no
information.

**`action`** — what is being done, in plain words, in order. One short sentence
per distinct thing. This is the field most searches hit.

**`shot`** — how it is framed: `selfie` `handheld` `locked-off` `over-shoulder`
`close-up` `wide` `insert`, and `vertical` or `horizontal`. Multiple allowed.
Read orientation off the frame itself; a rotation flag in the file lies often
enough that the frame wins.

**`products_visible`** — any product, packaging or device you can actually see.
Name it only if legible on screen; otherwise describe it (`grey face towel`,
`white pump bottle`). Never infer a brand from context. Empty list if none.

**`spoken`** — the two or three lines from the transcript that would make
someone pick this clip, quoted exactly. Quote, never paraphrase. Empty list if
there is no speech or the speech is inaudible.

**`talking_head`** — `true` only if a person is speaking to camera for most of
the clip. This is what separates a usable testimonial from b-roll.

**`usable_for`** — the honest short list of what this footage could carry:
`hook` `demo` `testimonial` `b-roll` `transformation` `reaction` `unusable`.
Judge on the footage alone — is it in focus, is it lit, does it hold a frame.
`unusable` is a real and useful answer; say it when the clip is a misfire, a
duplicate take, or too dark or shaky to cut with.

**`quality_notes`** — anything that would stop an editor using this: soft
focus, blown highlights, wind on the mic, a visible phone timer, a mirror
showing the crew. Empty list if it is clean.

**`confidence`** — `high` `medium` `low`, on the record as a whole. Go `low`
when frames are few, dark, or so similar that you are describing one moment
rather than a clip.

Two rules that outrank everything above:

**Say when you cannot tell.** `unknown` is always available and always
preferred to a plausible guess. A wrong record is worse than a thin one — a
thin record fails to surface, a wrong one surfaces the wrong footage into an ad.

**Use the same words every time.** The record is searched, not read. "bathroom"
every time, never "washroom" or "ensuite". "applying product" every time, never
"putting on cream". Consistency is what makes 3,000 records into an index
instead of 3,000 descriptions.
