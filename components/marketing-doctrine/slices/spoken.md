<!-- rendered from components/marketing-doctrine/frameworks.json by render.py — do not hand-edit -->

# Spoken copy — written for the mouth

Bound as `{spoken}`. Source: the doctrine component; refs are line pointers into the book, for verification only.

Spoken copy — the rules that turn a paragraph written for the eye into one written for the mouth, the colloquialism levels a script can run at, the register recipe per delivery style with the voice-model settings that match it, the punctuation map the voice model actually honours, and the demographic bands a colloquialism can be keyed to. The sections say what an ad argues, the techniques say how the argument is built, the delivery dials say how it is performed; this says how it is SAID, word by word, so the voice model reads it as a person and not as a page.

**Measured.** 2026-09-19 — a brief paragraph written with em-dashes was read by the voice model (eleven_multilingual_v2) with 1.3–1.7 s of silence at every dash; a 7 s paragraph took 11 s. The copy was written as prose and read as prose.

**The rule.** Every change from the written paragraph to the spoken one carries a rule from the table below and, at colloquialism level 3 or above, a research row or bank row quoted with its receipt. A room's word the writer supplied is the writer's word: it is cut back to the level the rows support. The meaning, every claim, every number and the offer survive the rewrite in sense; only the shape changes.

**Our creators outrank the web.** Where the brand has measured its own creators (runs/research/<brand>/creators/VOICEPRINTS.md — words per minute, sentence length, fragment rate, contraction rate, marker inventory, pause profile, per creator and rolled up per avatar), the spoken script matches THAT rhythm for the avatar it is written for, and the web sources below are the general frame. A creator who was measured outranks a source who was read. A brand with no voiceprints on file runs on the register recipe alone and says so.

## 0. The unit is the thought, not the sentence

**Ruled.** 2026-09-19 — the owner, on hearing scene 1 read as three clipped statements: "it doesn't feel like one complete sentence like it actually should" — "you still haven't understood how humans actually speak and translated that into copywriting." the owner's own rewrite is the reference: This is the old surface still sitting on your hand... That's why the sunscreen hasn't worked!

THE UNIT IS THE THOUGHT, NOT THE SENTENCE. A person says one thought in one breath; the punctuation is where they breathe, not where a grammar book would cut. Never chop a thought into a row of short statements — that reads as a list, and a list is not a person. Keep the thought whole and mark the breathing: an ellipsis (...) where the speaker pauses mid-thought before finishing it; a full stop where the thought ends; an exclamation or a question where the voice lifts because the point lands. A comma is a breath that does not stop.

| | |
|---|---|
| The prose | This — the old surface still sitting on your hand — is why the sunscreen hasn't worked. |
| Chopped (wrong) | This is the old surface. It's still sitting on your hand. That's why the sunscreen hasn't worked. |
| **Spoken (right)** | **This is the old surface still sitting on your hand... That's why the sunscreen hasn't worked!** |
| Why | the chopped version has three pitch resets and three full pauses for one thought; the spoken version has one thought, one mid-thought breath and one lift, and reads in 5 s against 7.3 s with the same words |

| Mark | What it is in speech |
|---|---|
| `...` | the mid-thought breath — the speaker pauses, the thought is not over; the voice model gives a short weighted pause (measured 0.33 s on eleven_multilingual_v2 at the vo4a settings) |
| `.` | the thought is over; pitch resets |
| `!` | the point lands; the voice lifts and the energy comes up for that clause |
| `,` | a breath inside the thought that does not stop it |
| `?` | the thought is handed to the viewer |

**Measured.** 2026-09-19, Susan's designed voice, eleven_multilingual_v2: the spoken_right line read in 5.02 s with pauses of 0.33 s and 0.47 s; the chopped version read in 7.25 s with pauses of 0.67, 1.07 and 0.91 s before the breath cut.

**The test.** Read the SPOKEN paragraph aloud once. If any full stop lands inside a thought a person would finish in one breath, it is a chop: join it back with a comma or an ellipsis. If a thought ends flat where the person would lean on it, it is missing its lift.

**The read the owner chose (2026-09-19, the owner: 'vo4a is way better' — the read chosen for the spot-hider avatar's voice).** stability 0.45 · similarity 0.8 · style 0.3 · speed 1.0 · speaker boost off. speaker boost OFF — it adds edge; the 'aggressive' tone the owner heard was the DESIGNED voice itself, which the voice designer rolls fresh each time with wild quality variance; the fix is a clone of a matched creator (creator-a), which the owner makes in the ElevenLabs app, then these settings on it

## 1. Written vs spoken — the rules of spoken copy

| Rule | Written | Spoken | Why | Receipt |
|---|---|---|---|---|
| `no-em-dash` | A dash hangs a second thought on the first — like this — and the eye takes it in one glance. | The hung thought stays in the same breath: a comma carries it, or an ellipsis marks the pause before the speaker finishes the thought. Never a dash; and never a full stop that chops one thought into two. | The dash is a written device for a break or an interruption with no spoken form; the listener hears only timing and pitch. The voice model reads it as a long silence, measured at 1.3–1.7 s per dash. | [the em-dash marks a break or interruption in writing](https://www.merriam-webster.com/grammar/em-dash-en-dash-how-to-use); [in dialogue the dash is a cut-off, the ellipsis a trailing off; neither is a sound](https://cmosshoptalk.com/2021/05/11/prose-interrupted-signaling-breaks-in-dialogue/); [dashes and ellipses are offered as pause devices on non-v3 models and called less consistent](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices) |
| `no-semicolon` | Two clauses held together with a semicolon; the reader supplies the relation. | Two sentences, or one joined with and, so or but. | Speech is grammatically intricate: many short clauses chained with conjunctions. Writing is lexically dense: fewer clauses packed with content. A semicolon is the dense form and has no spoken equivalent. | [Halliday: speech chains simple words in intricate clauses; writing packs complex words into simple sentences](https://reclaimingthelanguage.blog/2018/09/01/halliday-on-spoken-and-written-language/); [lexical density vs grammatical intricacy, with the two ways to compute density](https://www.atlantis-press.com/article/55913220.pdf) |
| `no-parenthesis` | The claim (with the qualification tucked inside brackets) reads as one line. | The qualification is its own sentence, or it is dropped into the next one with a comma. | Speakers verbalise one focus per intonation unit, typically one clause; an aside inside a clause is two foci in one unit, and the model has no way to say the brackets. | [Chafe: one focus of consciousness per intonation unit, mean 4.84 words, mode four](https://languagelog.ldc.upenn.edu/myl/Chafe1994IntonationUnits.pdf) |
| `ellipsis-is-the-breath` | A trailing thought... left for the reader to finish. | KEPT. The ellipsis is the mid-thought breath: the speaker pauses, the thought is not over. It is how a spoken paragraph stays one thought instead of a row of statements (the owner, 2026-09-19). | The ellipsis marks a trailing-off in writing; on the voice model it adds a pause with weight and is called less consistent than punctuation. | [ellipses add pauses and weight; as a break alternative they are less consistent](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices); [the ellipsis marks trailing off or a brief pause](https://cmosshoptalk.com/2021/05/11/prose-interrupted-signaling-breaks-in-dialogue/) |
| `one-idea-per-sentence` | A twenty-word sentence that carries the problem, its cause and the consequence in one nominal sweep. | Four to eight words a sentence. One idea each. The next idea gets the next sentence. | Conversational units average about five words and one clause; broadcast copy holds a sentence under twenty words so the announcer can breathe and the listener, who gets one pass, can follow. | [substantive intonation units: mean 4.84 words, about 60% a single clause](https://languagelog.ldc.upenn.edu/myl/Chafe1994IntonationUnits.pdf); [broadcast writing: sentences of twenty words or fewer, one idea per sentence](https://ask.ifas.ufl.edu/publication/WC193); [radio copy: short sentences deliverable in one breath, one idea per spot](https://killerspots.com/blog/how-to-write-a-radio-ad-script) |
| `fragments-allowed` | Every sentence is complete: subject, verb, object. | Fragments are allowed where a person would use one. "Not the sunscreen. The surface under it." | Over a third of all units in conversation are non-clausal and average about two words; a script with no fragments reads as written. | [Longman Grammar: non-clausal units are over a third of conversation, about two words each](http://tesl-ej.org/ej15/r14.html); [Biber's involved pole: conversation scores about +30 to +35, informational prose about -15](https://www.uni-bamberg.de/fileadmin/eng-ling/fs/Chapter_21/23DimensionsofEnglish.html) |
| `contractions-on` | It is not the product that is failing. You are not imagining it. | It's not the product that's failing. You're not imagining it. | Contractions are extremely common in speech and rare only in academic prose; the you-forms contract most of all. A read with no contractions marks the spot as amateur. | [COCA: you're / you'll / you've contract most; let's almost always contracted](https://stroppyeditor.wordpress.com/2015/10/12/contractions-which-are-common-and-which-arent/); [radio copy without contractions sounds stilted](https://killerspots.com/blog/how-to-write-a-radio-ad-script); [radio needs the contractions print avoids](https://journalism.university/broadcast-and-online-journalism/language-differences-radio-print/) |
| `pause-is-punctuation` | Pauses are typed in: (pause), (beat), a dash, a row of dots. | A pause is a full stop, at a main-clause boundary. A breath is a comma. Nothing else is written in. | Pauses fall at clause boundaries and are longer at main-clause boundaries; professional readers pause almost only at sentence boundaries. The voice model makes those pauses from the punctuation; anything typed in as a direction is read out loud. | [pause probability rises with clause-boundary strength; boundary pauses are longer](https://d-nb.info/1352428407/34); [professional readers pause almost only at sentence boundaries](https://www.isca-archive.org/icslp_2002/megyesi02_icslp.pdf); [descriptive direction inside the text is spoken aloud; write in a narrative style and let punctuation carry rhythm](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices) |
| `direct-address` | The one who checks the back of the hand under every light. | You check the back of your hand under every light. | Second-person pronouns are a top involved feature of speech; in advertising they raise involvement and hold attention, and the you-contractions are the most natural spoken forms. Not in every sentence: overuse has diminishing returns. | [second-person pronouns load on Biber's involved dimension](https://www.uni-bamberg.de/fileadmin/eng-ling/fs/Chapter_21/23DimensionsofEnglish.html); [66% of the print ads studied address the reader as you](https://www.tandfonline.com/doi/full/10.1080/08961530.2023.2215472); [eye-tracking: second-person ads hold more and longer fixations](https://www.tandfonline.com/doi/full/10.1080/15534510.2025.2522644); [readers preferred lower frequencies of you; overuse costs](https://arxiv.org/pdf/2101.11089) |
| `questions-to-the-viewer` | The problem is stated as a fact about the reader. | A real question opens ("Still coming back?"), the answer follows in the next sentence, and a rhetorical one may close a beat after its argument. | Real questions come before the argument they refer to, rhetorical ones after it; rhetorical questions help when the argument is strong and hurt when it is weak or the listener feels pushed. | [in ads, real questions precede the argument, rhetorical ones follow it](https://link.springer.com/article/10.1007/BF01017710); [rhetorical questions raise elaboration; they help strong arguments and hurt weak ones](https://www.researchgate.net/profile/Richard-Petty-2/publication/232475917_Effects_of_Rhetorical_Questions_on_Persuasion_A_Cognitive_Response_Analysis/links/02bfe50d05b140a476000000/Effects-of-Rhetorical-Questions-on-Persuasion-A-Cognitive-Response-Analysis.pdf); [a pushed audience resists the rhetorical question](https://journals.sagepub.com/doi/10.1177/0261927X06286380) |
| `restart-once` | Every sentence arrives finished. | One restart per paragraph at most, where the recipe allows it: "It's not, okay, it's not the sunscreen." Never in a proof or offer beat. | Self-initiated self-repair is the normal shape of talk and a little of it reads as authentic in a testimonial; it lowers credibility in an explainer, so it is a register option and never a default. | [self-repair within the same turn is the preferred shape](https://www.conversationanalysis.org/schegloff-media-archive/preference-for-self-correction-in-repair-in-conversation-1977/); [disfluent agents were judged more authentic to the task in one study](https://arxiv.org/pdf/2507.18315); [non-fluency lowers perceived credibility in an authority read](https://www.howcommunicationworks.com/blog/2021/5/9/credibility-how-to-be-seen-as-a-trustworthy-expert) |
| `fillers-at-the-start` | No fillers anywhere. | A filler or discourse marker, when the recipe allows one, sits at the START of a thought, never mid-phrase, and never more than one per forty to seventy-five words. | Fillers cluster at the start of intonation units; um announces a major delay and uh a minor one; you know invites the listener in and I mean flags a correction. In interviews you know runs about one per 500–1,300 words, so one per short script is the ceiling. | [Clark & Fox Tree: fillers are unit-initial 43 per 1,000 opportunities vs 13 mid-unit](http://www.columbia.edu/~rmk7/HC/HC_Readings/Clark_Fox.pdf); [you know invites inference; I mean flags an adjustment](https://www.maryvillecollege.edu/wp-content/uploads/Faculty/BehavioralSciences/cschrock/Fox-Tree-and-Schrock-2002.pdf); [you know 7–20 per 10,000 words; I mean 3–5](https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2024.1427062/full); [markers are conventional signals, not noise; usage shifts with formality and medium](https://people.ucsc.edu/~foxtree/Publications_files/FoxTree.2010.ms.pdf) |

## 2. Colloquialism levels — the dial

| Level | What it is | Contractions | Fillers | Discourse markers | Slang | In-words |
|---|---|---|---|---|---|---|
| **0 plain** | Clean broadcast speech. Short declaratives, the common contractions only, no fillers, no markers, no slang. The register a claim, a proof or a price is read in. | the common ones only (it's, that's, don't, isn't) | none | none | none | none |
| **1 conversational** | The way a careful person talks to one other person. Contractions throughout, one discourse marker per paragraph to open a thought (so, now, look, okay), direct address, a real question allowed. | on, throughout | none | one per paragraph, at the start of a thought (so · now · look · okay · right) | none | none |
| **2 casual** | Talking to a friend. Reduced forms where the recipe allows them (gonna, wanna, kinda), one filler per paragraph (honestly, I mean, you know), up to two markers, a fragment where a person would use one, a restart allowed once. | on, plus reduced forms (gonna · wanna · gotta · kinda) where the recipe allows | one per paragraph, at the start of a thought (honestly · I mean · you know · like) | up to two per paragraph | none | none |
| **3 slang** | The room's own words for the problem, the product and the result, dropped into casual speech. Everything level 2 allows, plus slang and in-words THE ROWS CARRY, quoted. | on, plus reduced forms | the room's own, from the rows, one or two per paragraph | the room's own openers, from the rows | only words a research row or bank row tagged in-word or subculture carries, quoted with the receipt | only from rows tagged in-word, quoted |
| **4 in-group** | The room talking to itself: its reaction lines, its openers and sign-offs, its reference points, the things it says that an outsider would not follow. Only where the rows show the room does this, and never on a claim. | on, plus reduced forms | the room's own, from the rows | the room's own openers and sign-offs, from rows tagged community-voice | from the rows, quoted | from the rows, quoted, including the room's reaction lines (RQ-24) |

### `0 plain`

- **Pattern:** Short declaratives. One idea each. A full stop between them. "It comes back in the same place. Every time. That's not the product failing."
- **Fits:** registers `clinical`, `plain-flat` · delivery styles `deadly-sincere`, `deadpan`, `understatement`, `hands-and-voiceover` · sections `proof`, `offer`, `call-to-action`, `product`
- **Receipt rule:** No receipt needed: this is the default every paragraph can fall back to.
- **Source:** https://killerspots.com/blog/how-to-write-a-radio-ad-script

### `1 conversational`

- **Pattern:** "So here's what's actually happening. The surface on your hand is old. It's still there. And the sunscreen's sitting on top of it."
- **Fits:** registers `warm-unhurried`, `plain-flat`, `clinical` · delivery styles `teacher-explainer`, `plain-testimonial`, `interview-consult`, `storyteller`, `deadly-sincere` · sections `hook`, `problem`, `root-cause`, `unique-mechanism`, `solution`, `objections`
- **Receipt rule:** The register recipe for the delivery style is the receipt; no room word is used, so no row is needed.
- **Source:** https://www.uni-bamberg.de/fileadmin/eng-ling/fs/Chapter_21/23DimensionsofEnglish.html

### `2 casual`

- **Pattern:** "Honestly? I thought it was the sunscreen. It's not. It's the old surface, still sitting there, and nothing's getting past it."
- **Fits:** registers `warm-unhurried`, `playful`, `intimate-low` · delivery styles `confessional`, `storyteller`, `plain-testimonial`, `reaction-duet` · sections `hook`, `problem`, `identification`, `agitation`, `failed-solutions`, `transformation`
- **Receipt rule:** The register recipe is the receipt for the filler set; reduced forms need the recipe's line that allows them. This is the CEILING when the research carries no in-word or community-voice row.
- **Source:** https://www.researchgate.net/publication/283979885_The_degree_of_grammaticalization_of_gotta_gonna_wanna_and_better_A_corpus_study

### `3 slang`

- **Pattern:** "⟨the room's word for the problem, quoted from the row⟩? Yeah. That's the old surface. ⟨the room's word for the fix, from the row⟩ first, then the rest."
- **Fits:** registers `playful`, `staccato-urgent`, `intimate-low` · delivery styles `rant`, `hype`, `reaction-duet`, `confessional` · sections `hook`, `problem`, `identification`, `agitation`, `failed-solutions`
- **Receipt rule:** LEVEL 3 IS QUOTED, NEVER INVENTED. Every slang word or in-word names the row it came from (post, timestamp or permalink). A word with no row is cut and the paragraph drops to level 2. Slang that originates in a community the avatar's profile does not place them in is not available at all (see the demographic bands).
- **Source:** https://pdfs.semanticscholar.org/20b0/6d67bac7b1929f5aad14a0377d6d95a0ce2c.pdf

### `4 in-group`

- **Pattern:** "⟨the room's opener, quoted from the row⟩. ⟨the room's reaction line, quoted⟩. ⟨the claim, at level 1 or below⟩."
- **Fits:** registers `playful`, `staccato-urgent` · delivery styles `reaction-duet`, `rant`, `hype` · sections `hook`, `identification`, `agitation`, `transformation`
- **Receipt rule:** Every line at this level quotes a row tagged community-voice, in-word or taste, with the receipt. The proof, product, offer and call-to-action beats never run at level 4: a claim said in in-group speech reads as a joke about the claim. A room the research shows is NOT ours (demographic fit) makes this level unavailable.
- **Source:** https://www.nbcnews.com/news/us-news/appreciation-appropriation-black-culture-shaping-gen-z-slang-rcna265993

## 3. Register recipes — per delivery style

Per delivery style (delivery.json → delivery_style), the spoken pattern the script follows and the voice-model settings that match it. Sentence length in words, the filler set the style may draw on, pause density, question use, whether a restart is allowed, the colloquialism levels the style can run at, the words-per-minute target band, and the eleven_multilingual_v2 voice_settings range.

**Voice settings.** The voice-settings guide: lowering stability broadens the emotional range and too low goes odd and fast; raising it flattens toward monotone; style exaggeration is recommended at 0 and costs stability; speed runs 0.7–1.2 with 1.0 the default. The API defaults are stability 0.5, similarity_boost 0.75, style 0, speed 1.0 (https://elevenlabs.io/docs/api-reference/text-to-speech/convert). The ranges below are craft within those stated limits, and a creator's measured voiceprint narrows them further for the avatar it belongs to. Doc: https://elevenlabs.io/docs/eleven-creative/playground/text-to-speech

**Words per minute.** Conversational voice-over runs about 150 words a minute, slow reads 120, retail promo 180; short-form creator speech is reported at 170–200 (https://www.teleprompter.com/blog/why-your-pace-of-speech-matters). A measured creator's own words per minute (VOICEPRINTS.md) outranks these bands for the avatar they attract. Doc: https://www.vowordcounter.com/articles/word-count-targets-by-spot-length/

| Delivery style | Sentence length | Fillers | Markers | Pause density | Questions | Restart | Levels | WPM | stability | style | speed | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `deadpan` | 4–8 words, even lengths, no lift at the end | none | so | high — a full stop after every line, a longer one before the punchline | none, or one flat rhetorical question after the argument | no | 0, 1 | 115–135 | 0.65–0.80 | 0.00–0.10 | 0.90–1.00 | https://arxiv.org/pdf/2605.00143 |
| `confessional` | 5–10 words, uneven, one longer run when the story turns | honestly, I mean, you know, um | so, okay, look | medium — a breath before the admission, a full stop after it | one real question to the viewer, answered by the speaker | once | 1, 2, 3 | 140–170 | 0.35–0.50 | 0.10–0.30 | 0.95–1.05 | https://www.sonicscope.org/pub/a59grfbl/release/2 |
| `teacher-explainer` | 6–12 words, one step per sentence, the step restated once | none | so, now, okay, right | medium — a full stop after each step, a comma inside it | confirmation checks ("right?", "see that?") after a step, and one real question to open | no | 0, 1 | 130–155 | 0.55–0.70 | 0.00–0.15 | 0.95–1.05 | https://www.wooclap.com/en/glossary/teacher-talk/ |
| `rant` | 3–9 words, stacked, repeated words for weight | like, honestly, seriously | okay, so, no, look | low — commas run on, one hard full stop before the closing understatement | stacked rhetorical questions after the grievance | once | 2, 3, 4 | 170–200 | 0.30–0.45 | 0.20–0.40 | 1.05–1.15 | craft — no linguistic source found for the rant register; treated as high-tempo storytelling with stacked rhetorical questions, intensifiers and few pauses (research memo, 2026-09-19) |
| `storyteller` | 6–12 words, chained with and, so, and then; a present-tense switch at the turn | you know | so, and then, anyway | medium — a full stop at each turn of the story, a longer one before the evaluation | one, at the evaluation ("and you know what that meant?") | once | 1, 2, 3 | 140–165 | 0.40–0.55 | 0.10–0.25 | 0.95–1.05 | https://www.ling.upenn.edu/~wlabov/sfs.html |
| `hype` | 2–7 words, subjects and copulas dropped, nominals stacked | okay, y'all, listen | okay, so, look, wait | low — commas, exclamations, one full stop before the reveal | rhetorical, rapid, unanswered until the reveal | no | 2, 3, 4 | 175–200 | 0.30–0.45 | 0.25–0.45 | 1.05–1.20 | https://www.sciencefriday.com/segments/sports-announcer-talk-linguistics/ |
| `plain-testimonial` | 5–10 words, first person, past tense then present | honestly | so, and, now | medium — a full stop after each thing that happened | none, or one real question the speaker once asked themself | once | 1, 2 | 135–160 | 0.45–0.60 | 0.05–0.20 | 0.95–1.05 | https://mailchimp.com/resources/testimonial-advertising/ |
| `deadly-sincere` | 4–9 words, level, no intensifiers | none | look, so | high — a full stop after every sentence, a held one before the claim | none | no | 0, 1 | 120–145 | 0.60–0.75 | 0.00–0.10 | 0.90–1.00 | https://www.researchgate.net/publication/388574168_INFLUENCER_AUTHENTICITY_AS_A_CATALYST_FOR_BRAND_TRUST_ANALYZING_ITS_IMPACT_ON_CONSUMER_PERCEPTION |
| `understatement` | 4–8 words, hedged (kind of, not bad), no amplifiers | none | so, anyway | high — a long full stop before the modest claim | none | no | 0, 1 | 115–140 | 0.65–0.80 | 0.00–0.10 | 0.90–1.00 | craft — no direct source; deadpan's cousin. Biber's amplifiers and emphatics list is the list of words to remove (https://www.uni-bamberg.de/fileadmin/eng-ling/fs/Chapter_21/23DimensionsofEnglish.html) |
| `interview-consult` | 6–12 words, answers to a question the viewer can hear | well, I mean | so, right, okay | medium — a beat after each question, a full stop after each answer | real questions, asked and then answered | once | 1, 2 | 135–160 | 0.45–0.60 | 0.05–0.20 | 0.95–1.05 | https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2024.1427062/full |
| `reaction-duet` | 2–7 words, reaction lines, the room's own | oh my gosh, wait, no | okay, so, wait | low to medium — a full stop after each reaction, the source's own timing between | rhetorical, to the source on screen | once | 2, 3, 4 | 150–190 | 0.30–0.50 | 0.15–0.35 | 1.00–1.10 | https://www.tandfonline.com/doi/full/10.1080/10509208.2024.2444051 |
| `hands-and-voiceover` | 5–10 words, one action per sentence, present tense | none | so, now, then | medium — a full stop where the hands finish a step | none, or one to open | no | 0, 1, 2 | 130–155 | 0.50–0.65 | 0.00–0.15 | 0.95–1.05 | https://killerspots.com/blog/radio-script-timer-how-long-is-a-30-second-script |

## 4. The voice-model punctuation map — `eleven_multilingual_v2`

What each mark does on the model the continuous track is made on, and what the take does with it. voice.py's for_reading() reads the `take` column; the brief's gate refuses every mark whose take is `replace` before the paragraph gets that far, so the take rules are the safety net for older briefs.

**Why this model.** request stitching — the one continuous read — runs on eleven_multilingual_v2 and is not available on eleven_v3 (https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/request-stitching). v2 is also the model the docs call most stable on long-form generation with the best number normalisation (https://elevenlabs.io/docs/overview/models).

Doc: https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices

| Mark | Name | What it does on the model | The take | Write it? | Source |
|---|---|---|---|---|---|
| `,` | comma | a breath — a short natural pause inside the sentence; the docs call standard punctuation the source of natural rhythm and the v3 note calls commas the breathing pattern | keep | yes — the breath | https://elevenlabs.io/blog/v3-audiotags |
| `.` | full stop | the beat — a sentence boundary, pitch reset and a clause-boundary pause, the one pause a person makes on purpose | keep | yes — the pause | https://d-nb.info/1352428407/34 |
| `?` | question mark | a lift at the end of the sentence; the model reads the question shape | keep | yes — where the recipe allows a question | https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices |
| `!` | exclamation mark | energy and emotional lift; the docs say exclamation marks influence emotional delivery. Sparingly — one per paragraph at most, and only in hype, rant or reaction registers | keep | sparingly | https://elevenlabs.io/docs/overview/capabilities/text-to-speech |
| `...` | ellipsis | THE MID-THOUGHT BREATH (the owner, 2026-09-19): kept, never replaced. A short weighted pause where the speaker has not finished the thought — measured 0.33 s at the vo4a settings. It is how a spoken paragraph stays one thought instead of a row of statements. | keep | never — a full stop instead | https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices |
| `…` | ellipsis character | THE MID-THOUGHT BREATH (the owner, 2026-09-19): kept, never replaced. A short weighted pause where the speaker has not finished the thought — measured 0.33 s at the vo4a settings. It is how a spoken paragraph stays one thought instead of a row of statements. | keep | never | https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices |
| `—` | em-dash | read as a long silence: measured 1.3–1.7 s at every dash on 2026-09-19. The docs offer dashes as a short-pause device on non-v3 models and call it less consistent; on this voice it was not short | replace with `, ` | never — a full stop or a comma instead | https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices |
| `–` | en-dash | the same as the em-dash | replace with `, ` | never | https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices |
| ` - ` | spaced hyphen as a dash | a short pause, less consistent (the docs' own words for the dash device) | replace with `, ` | never — a hyphen stays only inside a word (well-known) | https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices |
| `;` | semicolon | no documented behaviour; heard as a stall between two clauses the model cannot shape | replace with `. ` | never — two sentences instead | craft — no doc statement; the written-vs-spoken table's no-semicolon row is the rule |
| `(` | parenthesis | no documented behaviour; the aside is read flat with no way to hear the brackets | replace with `, ` | never — its own sentence instead | craft — no doc statement; the written-vs-spoken table's no-parenthesis row is the rule |
| `[tag]` | bracketed audio tag | an Eleven v3 feature ([laughs], [whispers], [sighs] and the rest); the docs introduce audio tags as v3's and do not say what v2 does with bracketed text, so on v2 it is unverified and treated as text that may be read aloud | replace with ` ` | never on v2 — the gate refuses brackets in the paragraph | https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices |
| `<break time="1.0s" />` | break tag | a natural pause of up to three seconds on the non-v3 models (v3 does not support it); too many in one generation cause instability — the model may speed up or add artefacts. The docs place it in the general controls section and do not name eleven_multilingual_v2 explicitly, so v2 support is by placement, not by a sentence | keep | not by the spoken script — a pause is a full stop; a break tag is a hand edit at the take, one per paragraph at most | https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices |
| `CAPS` | capitalisation | emphasis — the docs state it for v3 and the v3 note gives the example; on v2 it is weaker and unverified | keep | rarely — one word a paragraph, and only where the bracket names the emphasis | https://elevenlabs.io/blog/v3-audiotags |
| `$19.99` | numbers, currency, dates | text normalisation is on by default and v2 reads them best (a million dollars, not a thousand thousand); a spoken number is several spoken words, so it counts against the paragraph's size | keep | as figures, and count the spoken words | https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices |

**The settings, in one line each** (doc: https://elevenlabs.io/docs/eleven-creative/playground/text-to-speech): `stability` — randomness between generations — lower broadens the emotional range and too low goes odd and fast; higher goes monotone · `similarity_boost` — how closely the voice adheres to the original — high on poor source audio reproduces its artefacts; stays at the cast voice's own value · `style` — style exaggeration — amplifies the speaker's style at a cost to stability; the docs recommend 0 · `speed` — 0.7–1.2, default 1.0; extremes cost quality · `use_speaker_boost` — a subtle similarity boost; stays at the cast voice's own value

## 5. Demographic bands — options keyed to the profile

How colloquialism differs by age band, region and language community — as OPTIONS keyed to the avatar profile's own `### demographics` block (age · gender · skin tone / ethnicity · region · language), never as assumptions from a name or a face. Each band's markers are RESEARCHED, the gatherer fills the actual words per sub-avatar (RQ-22 to RQ-24), and where the brand has measured its own creators in the band, that measurement is the band.

**Rule.** A band is an OPTION keyed to the profile's demographics block, never an assumption from a name, a face or a room: it is reached for only when the block places the avatar in it, and a band's marker enters a script only through a research row or a bank row that shows the room using it. A band the profile does not name is not available, and a marker that belongs to a community the avatar is not in is not available even when the room borrows it.

**Our creators.** runs/research/<brand>/creators/VOICEPRINTS.md — 'By avatar' gives the measured band for each avatar the brand's creators attract: words per minute, sentence length, fragment rate, contraction rate, pauses, and the pooled marker inventory. Cited per sub-avatar in the spice pass through {voiceprint}.

### `age-55-plus-us` — profile slot `age`: 55 and over, US

- adults use look, listen, you know, I mean, well, you see about four times as often as children; marker use shifts with formality and setting
- older speakers use more canonical tag questions (isn't it, don't you) than younger ones
- you know runs as rapport at roughly one per 500–1,300 words in interview speech
- slang bands below the speaker's own generation read as borrowed; the room's own words come from its rows
- **Levels available:** `0`, `1`, `2`, `3`
- **Measured:** the brand's VOICEPRINTS.md 'By avatar' band for any avatar whose demographics put the age here — the creators' own words per minute, sentence length, fragments, contractions and markers are the band
- **Sources:** https://people.ucsc.edu/~foxtree/Publications_files/FoxTree.2010.ms.pdf · https://journals.sagepub.com/doi/10.1177/0075424206294369 · https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2024.1427062/full

### `age-gen-z` — profile slot `age`: roughly 18–29

- slang is a cultural marker, opaque to outsiders by design, working through semantic shift and pragmatic enrichment
- stance-taking phrases (it's giving) as a documented digital-slang device
- rizz, cap and no cap, lit, drip, slay, periodt originate in African American Language and Black queer culture; Black speakers are penalised for speech others are praised for, so these words are available only to an avatar the profile places in that community or to a creator who owns them
- **Levels available:** `1`, `2`, `3`, `4`
- **Measured:** none on file yet — the brand's VOICEPRINTS.md band for an avatar in this age range, when a creator in it is measured
- **Sources:** https://pdfs.semanticscholar.org/20b0/6d67bac7b1929f5aad14a0377d6d95a0ce2c.pdf · https://egarp.lt/index.php/EGJLLE/article/view/535 · https://www.nbcnews.com/news/us-news/appreciation-appropriation-black-culture-shaping-gen-z-slang-rcna265993 · https://languagedlife.ucla.edu/communications/from-slay-to-on-fleek-linguistic-features-of-millennial-and-gen-z-internet-communication/

### `region-us-south-sun-belt` — profile slot `region`: US South and Sun Belt (TX, FL, AZ, the Gulf and South Atlantic states)

- fixin' to as a near-future marker (South Atlantic and Gulf states); finna is its African American English form
- y'all — reported by 84% of Southerners and 49% of non-Southerners; the most distinctive Southern grammatical feature; also urban AAE
- double modals (might could) and fixin' to as Southern grammar; y'all carries the most regional capital
- bless your heart — sincere sympathy or condescension, decided by tone; the ironic use dated to 1732
- **Levels available:** `1`, `2`, `3`, `4`
- **Measured:** the brand's VOICEPRINTS.md band for any avatar whose demographics put the region here — a creator from the region who was measured is the band, and the marker enters only where the rows show the room using it
- **Sources:** https://ygdp.yale.edu/phenomena/fixin-to · https://en.wikipedia.org/wiki/Y'all · https://books.google.com/books/about/American_English.html?id=vPdgBgAAQBAJ · https://en.wikipedia.org/wiki/Bless_your_heart · https://dare.wisc.edu/

### `community-african-american-english` — profile slot `skin tone / ethnicity`: African American English speakers (only when the profile states it)

- a rule-governed system: habitual and invariant be, stressed BIN, be done, stressed STAY, and rhetorical strategies — signifying, marking, loud-talking
- copula absence, habitual be, is-levelling, and the performative delivery of preachers, comedians and singers
- media reinforce accent stereotypes and cast standard speakers as the good guys — the guardrail: never a feature used as a comic or streetwise shorthand, never on an avatar the profile does not place here
- **Levels available:** `1`, `2`, `3`, `4`
- **Measured:** none on file — available only through a measured creator the profile places in this community
- **Sources:** https://www.cambridge.org/core/books/african-american-english/1AE59657F9CF1BBC3A2BF2B9BB29D1D0 · https://stanfordmag.org/contents/in-praise-of-spoken-soul · https://linguistlist.org/issues/23/3439/ · https://ygdp.yale.edu/african-american-language-and-grammatical-diversity-2020

### `community-latino-chicano-english` — profile slot `skin tone / ethnicity`: Latino / Chicano English speakers (only when the profile states it)

- a native English dialect shaped by Spanish contact, spoken by monolinguals too, and central to young Latino identity
- in-group address terms (homie, ese) mark membership and are not available to an avatar outside it
- **Levels available:** `1`, `2`, `3`, `4`
- **Measured:** none on file — available only through a measured creator the profile places in this community
- **Sources:** https://link.springer.com/book/10.1057/9780230510012 · https://www.pbs.org/speak/seatosea/americanvarieties/chicano/

### `region-british-vs-american` — profile slot `region`: British English (when the profile's region is the UK)

- innit is lexicalising into an invariant tag; right, innit and yeah peak in adolescence and drop in adults
- British speakers use tag questions far more than Americans, and older speakers use canonical tags
- please behaves differently as a politeness marker in American and British English
- American English leads on gonna, wanna, gotta — the reduced forms read as American and fast
- **Levels available:** `0`, `1`, `2`, `3`
- **Measured:** none on file
- **Sources:** https://www.semanticscholar.org/paper/British-English-is-developing-a-new-discourse-innit-Krug/8285844f056a1a4a16d81b9a85c83ce3b763f30b · https://journals.sagepub.com/doi/10.1177/0075424206294369 · https://www.cambridge.org/core/journals/english-language-and-linguistics/article/separated-by-a-common-impoliteness-marker-please-in-american-and-british-webbased-english/3EDE29FABD5DB11786565545E0DC1664 · https://www.researchgate.net/publication/283979885_The_degree_of_grammaticalization_of_gotta_gonna_wanna_and_better_A_corpus_study

### `medium-short-form-creator` — profile slot `language`: the medium band: short-form creator speech vs broadcast voice-over (applies to every avatar reached through a creator format)

- creator scripts sound like a recommendation to a friend: a hook inside two or three seconds, the pain point addressed directly, open questions, slang where the room uses it
- incomplete sentences, repeated words for emphasis, mid-sentence hooks; the anti-script test — read it aloud and rewrite anything that sounds like an ad
- tempo: short-form 170–200 words a minute vs 140–160 long-form and 120–150 ordinary conversation
- close-up direct address reads as one-to-one talk and invites a parasocial response; broadcast readers pause only at sentence boundaries
- **Levels available:** `1`, `2`, `3`, `4`
- **Measured:** the brand's VOICEPRINTS.md — every measured creator is in this band, and the 'By avatar' figures are its actual numbers for our rooms
- **Sources:** https://inbeat.agency/blog/ugc-scripts · https://vidlo.video/blog/a-complete-guide-to-writing-viral-ugc-scripts/ · https://www.teleprompter.com/blog/why-your-pace-of-speech-matters · https://www.tandfonline.com/doi/full/10.1080/10509208.2024.2444051 · https://www.isca-archive.org/icslp_2002/megyesi02_icslp.pdf

## 6. The spoken research questions — what the gatherer fills

| Id | Question | Tags | Feeds |
|---|---|---|---|
| RQ-22 | How does this room actually phrase things OUT LOUD — its fillers, its openers, its sign-offs, the words it starts a thought with and the words it ends one on — as heard in its own posts, comments and videos, never as written copy? | `in-word`, `subculture`, `community-voice` | 4g-spice, 5-brief |
| RQ-23 | What does this room CALL things — the in-words for the problem, the product category, the result and the people involved — the shorthand it uses among itself rather than the category's own names? | `in-word`, `subculture`, `taste` | 4g-spice, 4d-expansion |
| RQ-24 | How does this room REACT — the reaction lines it drops when something works, fails, surprises or disgusts it — quoted as said, so a beat can land in the room's own reflex rather than a writer's? | `community-voice`, `in-word`, `taste` | 4g-spice, 4e-close |
