# Held prompt versions: not live, for review (2026-11-18)

Each file is its base, byte for byte, plus the marked blocks below. Nothing here runs: the writing line
names its prompts by hand, and the two `proposed/` folders are not read by the picker. Built by
`build_held.py` from `recipes.json` and `blocks/`; run it again to rebuild or to try another base.

| Item | File | What changes | Decision it fills |
|---|---|---|---|
| `idea` | `components/video-writing/prompts/v2/stage4i-idea-v3-owner.md` (base: `stage4i-idea-v2-owner.md`) | The pass is handed the brand's angle list, chooses the angle before the idea, names the concept under it, and ends its answer with five labelled lines (ANGLE, ANGLE BELIEF, ANGLE GAP, CONCEPT, CONCEPT WHY). Candidates, scores and the tie rule are untouched. | 2.2 Which angle · 2.3 Which concept under the angle |
| `brief` | `components/video-writing/prompts/v2/stage5-ai-brief-v16-owner.md` (base: `stage5-ai-brief-v13-owner.md`) | The brief is handed the idea pass's answer and carries it by name: one Idea / Concept line under the concept's paragraph, and piece.idea and piece.concept in the block. piece.angle keeps its base rule. Nothing else about the brief changes. | 4.2 The one idea · 4.11 What goes to production |
| `hooks` | `components/video-writing/prompts/v2/stage4v2a-readhooks-v11-owner.md` (base: `stage4v2a-readhooks-v9-owner.md`) | Says along what line the six openings differ (each takes a different customer-language angle), why the entry level sets how wide an opening reaches, and adds one labelled line per opening: CUSTOMER ANGLE V0 to V5. No test, slot or hook-matrix key changes. | 4.4 How the openings differ from each other |
| `build` | `components/video-writing/prompts/v2/stage4v2b-build-v11-owner.md` (base: `stage4v2b-build-v9-owner.md`) | One short block where the placement is first planned: what the lead and the body are for. No beat, section, slot, check or output line is added. | 4.5 The lead and the body |
| `audit` | `components/video-writing/prompts/v2/stage4e-audit-v13-owner.md` (base: `stage4e-audit-v11-owner.md`) | The same short block of reasoning the held spice pass carries, plus a note the audit prints last: where the sale starts as a share of the runtime, and any line that reads stiff aloud. No new check, no CHECK TABLE row, no FAIL, no change to a verdict word. | 4.8 How native and how sales it reads |
| `spice` | `components/video-writing/prompts/v2/stage4g-spice-v11-owner.md` (base: `stage4g-spice-v9-owner.md`) | The same short block of reasoning the held audit carries, placed where the pass's own work starts. No slot, gate or output line is added and no beat moves. | 4.8 How native and how sales it reads |
| `awareness` | `components/video-writing/prompts/stage-1b-audience/proposed/stage1b-audience-v15-owner.md` (base: `stage1b-audience-v13-owner.md`) | The level is read off the post itself on every swipe, and AWARENESS WHY always says what the post shows. A declared level holds exactly as before; where the post reads at another level, AWARENESS WHY says so in the same line, as a finding. No label changes. | 1.6 Its awareness level |
| `creator-brief` | `components/video-writing/prompts/stage-5-brief/creator-lane/proposed/stage5-creator-brief-v37-owner.md` (base: `stage5-creator-brief-v36-owner.md`) | The brief is handed the format by name with its reasons (one new slot) and names it in its header; and it prints which parts are fixed (the angle, the key points, the product facts, the ask) and which are the creator's own (the words, the slang, the delivery). The script stays whole. | 4.10 A creator's or founder's brief |
| `creator-page` | `components/video-writing/prompts/stage-7b-page/proposed/stage7b-concept-v11-owner.md` (base: `stage7b-concept-v10-owner.md`, unsaved in the shared folder) | The page is handed the format by name (one new slot) and the Format line names it; the angle and key points are fixed, the words, slang and delivery are the creator's, because too exact reads as an ad. Labels the code reads are unchanged. | 4.10 A creator's or founder's brief |
| `format-call` | `components/video-teardown/prompts/proposed/format-call-guidance-v1-owner.md` (new file) | New. The short guidance shown to the person deciding: decide by the structure, and one line each on when to choose Same as X, Its own format, Not a format. | 3.3 A format the lists do not know |
| `scratch-picks` | `components/video-writing/prompts/proposed/stage2s-scratch-picks-v1-owner.md` (new file) | New. States the order the picks are made in (the avatar side first: angle, language, tone; then the format the avatar already watches, by the awareness level the ad enters at) and asks for one reason line per pick, as eight labelled lines. | 2.4 An idea with no swipe: format, style, arc |

## idea — 4i · the controlling idea (writing v2)

- **Fills:** 2.2 Which angle · 2.3 Which concept under the angle
- **Base:** `components/video-teardown/prompts/proposed/stage4i-idea-v2-owner.md`
- **Out:** `components/video-writing/prompts/v2/stage4i-idea-v3-owner.md`
- **New slots:** `{angles}`
- **Applies to the other base:** yes — stage4i-idea-v1-owner.md: version note and 3 block(s) placed, every anchor found once
- **Where the words come from:** Decision 2.2 fill for the angle steps and decision 2.3 fill for the concept, sentence for sentence. Added beyond the fill, each a guard and not reasoning: the angle is one id from the list and never written new; what to print when the list holds no angle; the sentence that keeps the base's other use of the word angle (a lens or door) as written.

### idea · change 1 of 4: version note

**Before** (the note goes above the base's first line):

```
<!-- writing v2 (2026-11-02, V56): a new pass between the injection and the hooks. One controlling idea, chosen before a line of the middle is written. -->
```

**After** (the text added):

```
<!-- writing v2 (2026-11-18, held for review, not live): stage4i-idea-v3 = v2 + THE ANGLE and THE CONCEPT (fills decisions 2.2 and 2.3 of the video decision logic). The pass is handed the brand's angle list in one new slot, `angles`, chooses the angle before the idea and names the concept under it. Five labelled lines are added at the end of the answer: ANGLE, ANGLE BELIEF, ANGLE GAP, CONCEPT, CONCEPT WHY. Every line of v2 stands, word for word: the candidates, the scores and the tie rule are unchanged. -->
```

### idea · change 2 of 4: the angle list is handed in

**Before** (the block goes under this text of the base):

```
Real moves from real high-performing scripts, by section: {creative_moves}
```

**After** (the text added):

```
The brand's angle list, each angle with its id, its name, the one sentence it argues and the avatar it is aimed at: {angles}
```

### idea · change 3 of 4: the angle and the concept, before the idea

**Before** (the block goes above this text of the base):

```
## What a controlling idea is
```

**After** (the text added):

```
## The angle, chosen before the idea (v3)

Choose the angle before you look for the idea. An angle here is one row of the brand's angle list above: what the brand argues. Wherever else this prompt uses the word angle for a lens or a door into the ad, that is a different thing and it stays as written.

How to choose it:

1. Start from what customers say: the real customer language above.
2. Find the belief they already hold.
3. An angle agrees with that belief, shows where it falls short, and puts the new information in that gap. Look for the angles on the list that do this.
4. Order them by how broad the entry belief is.
5. A reworded winner is not a new angle.

Choose one angle from the list, by its id. Never write an angle that is not on the list. If the list holds no angle, print `ANGLE: none on file` and `none` on the two lines under it, and carry on.

## The concept, named under the angle (v3)

The order is: angle, then concepts, then videos, then scroll stoppers, then hooks. So the concept is named next, under the angle.

A concept is the voice and the situation that carries the angle. It comes from one real experience, or from the culture the audience follows. A winner becomes a new concept under the same angle.

Name the concept this script runs under the angle you chose. Give it a short name, and say in one line the voice, the situation and where it comes from. If no angle was chosen, print `CONCEPT: none` and `CONCEPT WHY: none`.

Then find the controlling idea as the sections below say. Nothing in them changes: the five candidates, the scores and the tie rule stand as written.
```

### idea · change 4 of 4: five labelled lines at the end of the answer

**Before** (the block goes under this text of the base):

```
Then the five candidates with their scores, so the owner can see what lost.
```

**After** (the text added):

````
Last, five labelled lines (v3). One per line, spelled exactly this way, nothing else on the line. Later steps read them by these labels:

```
ANGLE: <id from the list> — <its name>
ANGLE BELIEF: <the belief the customer already holds>
ANGLE GAP: <where it falls short; the new information>
CONCEPT: <a short name>
CONCEPT WHY: <one line: the voice, the situation, and the real experience or the culture it comes from>
```
````

## brief — 5 · the brief, AI lane (writing v2)

- **Fills:** 4.2 The one idea · 4.11 What goes to production
- **Base:** `components/video-writing/prompts/v2/stage5-ai-brief-v13-owner.md`
- **Out:** `components/video-writing/prompts/v2/stage5-ai-brief-v16-owner.md`
- **New slots:** `{controlling_idea}`
- **Applies to the other base:** yes — stage5-ai-brief-v15-owner.md: version note and 4 block(s) placed, every anchor found once
- **Also checked:** `components/video-teardown/prompts/proposed/stage5-ai-brief-v13-owner.md` — applies (version note and 4 block(s) placed, every anchor found once)
- **Where the words come from:** Decisions 4.2 and 4.11 have no fill text; the wording follows their carry lines (the brief never receives the idea by name; the brief is the one file that goes to production). piece.angle already stands in the base (one id from the angles list, never blank) and is left as written; the block only says the idea pass's ANGLE id is that id when it is on the list.

### brief · change 1 of 5: version note

**Before** (the note goes above the base's first line):

```
<!-- stage5-ai-brief-v13-the owner = v12 + A SCENE IS ONE MOMENT (owner, 2026-11-09: AI video kept coming out as single clips with no sequence inside the scene; a back-and-forth was written as one scene per line). Speakers live on lines. Everything else stands, wo [... the line goes on]
```

**After** (the text added):

```
<!-- stage5-ai-brief-v16 (2026-11-18, held for review, not live) = v13 + THE ONE IDEA, CARRIED BY NAME (fills decisions 4.2 and 4.11 of the video decision logic): the brief is handed the idea pass's answer in one new slot, `controlling_idea`, and carries it by name: one Idea line under the concept's paragraph, and `piece.idea` and `piece.concept` in the block. `piece.angle` keeps its rule. No scene, line, shot or check changes. Everything else stands, word for word. -->
```

### brief · change 2 of 5: the one idea is handed in

**Before** (the block goes above this text of the base):

```
Here are the transformed scripts, one per source format: {stage4_outputs}
Here is the hook set, with every variation and its scroll stopper: {hook_set}
Here is where the ad starts — the line the owner chose, word for word, or `none`: {opening_at}
When it names a line, the piece STARTS there: every scene of the injection before that line is left out of the brief — no scene, no voice line, no picture for it — and the openings are the hook set's, built on that line. When it says `none`, nothing is cut.
```

**After** (the text added):

```
Here is the one idea this piece runs on, as the idea pass handed it on: {controlling_idea}
```

### brief · change 3 of 5: the rule: carry it by name

**Before** (the block goes above this text of the base):

```
## THE BRIEF IS THE PROMPT — YOUR OUTPUT HAS TWO PARTS
```

**After** (the text added):

```
## THE ONE IDEA — carried by name (v16)

The one idea this piece runs on is among the inputs above, as the idea pass
handed it on. The script was already written inside it. The brief is the one
file that goes to production, so the idea travels in it, by name. Nothing else
about the brief changes: no scene, no line and no shot is written, moved or
cut because of this section.

Carry it in three places:

- **The readable view** — one line under the concept's paragraph, naming the
  idea and the concept (the shape below shows it).
- **`piece.idea`** — the controlling idea in one line: the line the idea pass
  printed under THE CONTROLLING IDEA, copied, never reworded.
- **`piece.concept`** — the name on the idea pass's `CONCEPT:` line; an empty
  string when the idea pass named none. It is never the `# ` heading: the
  heading names this piece and is `piece.title`.

`piece.angle` keeps its rule: one id from the angles list. Where the idea pass
printed an `ANGLE:` line and its id is on that list, that is the id.

When that input is empty or reads `[UNFILLED]`, `piece.idea` and
`piece.concept` are empty strings and the view's line says `none`.
```

### brief · change 4 of 5: one line in the header prose

**Before** (the block goes under this text of the base):

```
⟨One to three sentences: the core idea this concept runs on, pulled from its
own material.⟩
```

**After** (the text added):

```
**Idea:** ⟨the controlling idea in one line, as the idea pass printed it — or `none`⟩ · **Concept:** ⟨the concept's name from the idea pass's `CONCEPT:` line — or `none` when it named none⟩
```

### brief · change 5 of 5: piece.idea and piece.concept in the block

**Before** (the block goes under this text of the base):

```
  "awareness": "⟨the awareness level this piece enters on⟩",
  "sophistication": "⟨the sophistication stage⟩",
  "product": "⟨the product's folder name under the brand's products — the one whose real photo the edit lays on⟩",
  "angle": "⟨the angle this piece argues: one id from the angles list, spelled as that list spells it⟩",
```

**After** (the text added):

```
  "idea": "⟨the controlling idea in one line — the line the idea pass printed under THE CONTROLLING IDEA, copied; an empty string when the idea is empty⟩",
  "concept": "⟨the concept's name from the idea pass's `CONCEPT:` line; an empty string when the idea pass named none⟩",
```

## hooks — 4ab · reading + hooks (writing v2)

- **Fills:** 4.4 How the openings differ from each other
- **Base:** `components/video-teardown/prompts/proposed/stage4v2a-readhooks-v9-owner.md`
- **Out:** `components/video-writing/prompts/v2/stage4v2a-readhooks-v11-owner.md`
- **New slots:** none
- **Applies to the other base:** yes — stage4v2a-readhooks-v10-owner.md: version note and 2 block(s) placed, every anchor found once
- **Where the words come from:** Decision 4.4 fill, sentence for sentence. The label is CUSTOMER ANGLE Vn, not ANGLE Vn, because the base already uses ANGLE as a tag for marketer-drafted language in its SOURCE check. Added beyond the fill, as guards: the control is named and not rewritten; the entry level stays the reading's; nothing parsed changes.

### hooks · change 1 of 3: version note

**Before** (the note goes above the base's first line):

```
<!-- writing v2 (2026-11-07): stage4v2a-readhooks-v9 = v8 + THE MENU: three ways in judged by the first frame, six opening types with the dead openings banned, and a ten-line battery (two per trigger) the five variations are taken from. New output: section 2b, [... the line goes on]
```

**After** (the text added):

```
<!-- writing v2 (2026-11-18, held for review, not live): stage4v2a-readhooks-v11 = v9 + EACH OPENING TAKES A DIFFERENT CUSTOMER-LANGUAGE ANGLE (fills decision 4.4 of the video decision logic): the line the six openings differ along, why the entry level sets how wide an opening reaches, and one new labelled line per opening, CUSTOMER ANGLE V0 to V5. No test is added or changed; the five slots and the hook-matrix block are untouched. Everything else is v9, word for word. -->
```

### hooks · change 2 of 3: the line the openings differ along

**Before** (the block goes under this text of the base):

```
that a viewer would read as the same opening are one variation. What every
take keeps from the format is its WORLD — the speaker, the register, the
reference the culture read names, the place the body continues in — so the
body that follows can carry any of the six.
```

**After** (the text added):

```
**EACH OPENING TAKES A DIFFERENT CUSTOMER-LANGUAGE ANGLE (v11).** This
is the line the six openings differ along. A customer-language angle is one
thing customers say, in their own words, from the language above. The take is
the moment an opening enters through; its customer-language angle is what
customers say that it comes in on. Each opening takes a different one, so the
set shows which one opens the conversation. The control is not rewritten for
this: name the angle its line already takes.

How wide an opening reaches follows the entry level the reading names. That
level is already decided; this is the reason it holds:

- For the widest market, open on something unexpected without naming the
  problem. That is the unaware entry, and THE UNAWARE ENTRY above says what
  may be in it.
- To reach only people with the problem, name it. That is the problem-aware
  entry.

Print the angle as one more labelled line under each opening's `THUMB` line,
V0 to V5, one per line and nothing else on the line:

`CUSTOMER ANGLE Vn: <the angle, in a few of the customer's own words> · <the row it comes from; on V0, control>`

This adds no test and changes none. `TAKE`, `LINE`, `CARD`, `SCROLL`, `THUMB`
and the `hook-matrix` block stay exactly as they are.
```

### hooks · change 3 of 3: the labelled line, beside the five slots

**Before** (the block goes under this text of the base):

```
the one still, what is in it and where, and its words. Then: every specific
in the take and the verbatim it came from **quoted inside its original full
sentence**, with its source · what it assumes about the speaker · how the
take hands over to the body's next beat.
```

**After** (the text added):

```
Then one more labelled line for each opening, V0 included, under its `THUMB`
line: `CUSTOMER ANGLE Vn:`, as EACH OPENING TAKES A DIFFERENT
CUSTOMER-LANGUAGE ANGLE above says (v11).
```

## build — 4cde · placement + expansion + close (writing v2)

- **Fills:** 4.5 The lead and the body
- **Base:** `components/video-writing/prompts/v2/stage4v2b-build-v9-owner.md`
- **Out:** `components/video-writing/prompts/v2/stage4v2b-build-v11-owner.md`
- **New slots:** none
- **Applies to the other base:** yes — stage4v2b-build-v10-owner.md: version note and 1 block(s) placed, every anchor found once
- **Also checked:** `components/video-teardown/prompts/proposed/stage4v2b-build-v10-owner.md` — applies (version note and 1 block(s) placed, every anchor found once)
- **Where the words come from:** Decision 4.5 fill, sentence for sentence. From components/video-writing/AD-BODIES.md: only the words 'everything after the hook' (its line 7: 'A **body** is everything after the hook: the part that sells.'). AD-BODIES.md holds the steps for building a body; it has no sentence on what a lead or a body is for, so nothing else is taken from it. Its step 3 (each hook gets its own one-line lead-in) is not used: it would add a writing job the fill does not ask for.

### build · change 1 of 2: version note

**Before** (the note goes above the base's first line):

```
<!-- writing v2 (2026-11-03): stage4v2b-build-v9 = v8 + THE SKIT RULES, from the first full world skit. Everything else stands, word for word. -->
```

**After** (the text added):

```
<!-- writing v2 (2026-11-18, held for review, not live): stage4v2b-build-v11 = v9 + WHAT THE LEAD AND THE BODY ARE FOR (fills decision 4.5 of the video decision logic): one short block of reasoning where the placement is first planned. It adds no beat, section, slot, check or output line. Everything else stands, word for word. -->
```

### build · change 2 of 2: what the lead and the body are for

**Before** (the block goes under this text of the base):

```
Plan the direct-response transformation. The lane, the opening beat and the
awareness entry are already decided and handed to you above — do not re-derive
them, do not overrule them. Your job starts after the opening.
```

**After** (the text added):

```
**WHAT THE LEAD AND THE BODY ARE FOR (v11).** Plan with these two jobs
in mind. They are why the beats after the opening exist:

- **The lead** comes once the opening lands. It carries the conversation on,
  and it sets the tone.
- **The body** is everything after the hook. It earns trust through story
  before the product appears: I see you, I went through it, here is what I
  learned. Skip that and you get buyers who refund.

This is reasoning for the plan. It adds no beat, no section and no check, and
it changes no rule below.
```

## audit — 4f · the audit (writing v2)

- **Fills:** 4.8 How native and how sales it reads
- **Base:** `components/video-writing/prompts/v2/stage4e-audit-v11-owner.md`
- **Out:** `components/video-writing/prompts/v2/stage4e-audit-v13-owner.md`
- **New slots:** none
- **Applies to the other base:** yes — stage4e-audit-v12-owner.md: version note and 1 block(s) placed, every anchor found once
- **Also checked:** `components/video-teardown/prompts/proposed/stage4e-audit-v12-owner.md` — applies (version note and 1 block(s) placed, every anchor found once)
- **Where the words come from:** Decision 4.8 fill, sentence for sentence, in the block both passes share. The note's two lines are the two things the task names. 'Where the sale starts' is read as the beat where the product enters. The printed heading line says 'a note, not a fix' because the audit's whole answer is handed to the patch pass on a re-run.

### audit · change 1 of 2: version note

**Before** (the note goes above the base's first line):

```
<!-- writing v2 (2026-11-03): stage4e-audit-v11 = v10 + check 13, the skit test. -->
```

**After** (the text added):

```
<!-- writing v2 (2026-11-18, held for review, not live): stage4e-audit-v13 = v11 + HOW NATIVE IT READS, AND WHERE THE SALE SITS, with THE NATIVE NOTE (fills decision 4.8 of the video decision logic): the same block of reasoning the held spice pass carries, and a note of two labelled lines printed after WHAT I WOULD WATCH (where the sale starts as a share of the runtime; any line that reads stiff aloud). It adds no check, no CHECK TABLE row and no FAIL, and changes no verdict word. Everything else stands, word for word. -->
```

### audit · change 2 of 2: the reasoning, and the note printed last

**Before** (the block goes under this text of the base):

```
**WHAT I WOULD WATCH** — the one thing most likely to be wrong that these
checks cannot catch. Say it plainly rather than padding the verdict.
```

**After** (the text added):

```
**HOW NATIVE IT READS, AND WHERE THE SALE SITS (v13).** The reasoning,
in three lines:

- The organic feel carries the piece, and the sale sits in the back half.
- It should read like a favour from a friend.
- Reading it aloud is what catches the stiff lines and the machine-written
  ones.

This is reasoning only. It adds no check, no gate and no hold, and it changes
no rule in this prompt.

**THE NATIVE NOTE (v13)** — the last thing this audit prints, after WHAT
I WOULD WATCH. One heading line, then two labelled lines, one per line:

`THE NATIVE NOTE (a note, not a fix):`
`SALE STARTS: <time> of <runtime> · <n>% in · <first half or back half>`
`STIFF ALOUD: "<the line>" (<time>) ; … — or none`

- `SALE STARTS` is where the sale starts, as a share of the runtime: the time
  of the first beat that sells (the beat where the product enters), over the
  script's own runtime.
- `STIFF ALOUD` is every line that reads stiff or machine-written when it is
  read aloud, quoted.

This is a note and only a note. It adds no new check. It adds no row to the
CHECK TABLE and no FAIL. It changes no verdict word: SHIP, RE-RUN and STOP are
decided exactly as before, and nothing in this note sends a script back.
```

## spice — 4g · the creative pass (writing v2)

- **Fills:** 4.8 How native and how sales it reads
- **Base:** `components/video-writing/prompts/v2/stage4g-spice-v9-owner.md`
- **Out:** `components/video-writing/prompts/v2/stage4g-spice-v11-owner.md`
- **New slots:** none
- **Applies to the other base:** yes — stage4g-spice-v10-owner.md: version note and 1 block(s) placed, every anchor found once
- **Also checked:** `components/video-teardown/prompts/proposed/stage4g-spice-v10-owner.md` — applies (version note and 1 block(s) placed, every anchor found once)
- **Where the words come from:** Decision 4.8 fill, sentence for sentence. The block file is the first part of the audit's block, byte for byte (the build checks it).

### spice · change 1 of 2: version note

**Before** (the note goes above the base's first line):

```
<!-- writing v2 (2026-11-02, V56): stage4g-spice-v9 = v8 + THE CREATIVE REWRITE: ideas may change, facts stay locked. -->
```

**After** (the text added):

```
<!-- writing v2 (2026-11-18, held for review, not live): stage4g-spice-v11 = v9 + HOW NATIVE IT READS, AND WHERE THE SALE SITS (fills decision 4.8 of the video decision logic): one short block of reasoning, the same block the held audit carries. It adds no slot, gate or output line and moves no beat. Everything else stands, word for word. -->
```

### spice · change 2 of 2: the reasoning

**Before** (the block goes above this text of the base):

```
The clean injection is done — the sense is locked. This pass adds the
flare: why this format works for *this* avatar, and what makes it stand
out. **The facts are locked: every claim, number, price, guarantee, product fact,
customer quote, the order of the argument and the offer stay as handed in.**
```

**After** (the text added):

```
**HOW NATIVE IT READS, AND WHERE THE SALE SITS (v11).** The reasoning,
in three lines:

- The organic feel carries the piece, and the sale sits in the back half.
- It should read like a favour from a friend.
- Reading it aloud is what catches the stiff lines and the machine-written
  ones.

This is reasoning only. It adds no check, no gate and no hold, and it changes
no rule in this prompt.
```

## awareness — 1b · the audience read

- **Fills:** 1.6 Its awareness level
- **Base:** `components/video-writing/prompts/stage-1b-audience/stage1b-audience-v13-owner.md`
- **Out:** `components/video-writing/prompts/stage-1b-audience/proposed/stage1b-audience-v15-owner.md`
- **New slots:** none
- **Applies to the other base:** n/a — no other base was named for this item
- **Also checked:** `components/video-teardown/prompts/proposed/stage1b-audience-v14-owner.md` — applies (version note and 1 block(s) placed, every anchor found once)
- **Also checked:** `components/video-writing/prompts/stage-1b-audience/stage1b-audience-v12-owner.md` — applies (version note and 1 block(s) placed, every anchor found once)
- **Where the words come from:** Decision 1.6 fill, sentence for sentence. Added beyond the fill, as guards: the base's own rule that the source's reading is taken from the doctrine read and never re-derived; AWARENESS WHY stays one line because the code reads it as one line; a finding changes no label.

### awareness · change 1 of 2: version note

**Before** (the note goes above the base's newest version note):

```
*v12 (2026-10-06, the owner: "i mean not every add is funny...." · "it's more about the foundational way to identify these cultural nuances"): STRAIGHT is the default. The HUMOR RUNG ladder now starts at 0 · straight, and 0 is what a piece gets unless the swip [... the line goes on]
```

**After** (the text added):

```
*v15 (2026-11-18, held for review, not live: it sits in `proposed/`, which the picker does not read; fills decision 1.6 of the video decision logic): the awareness level is read off the post itself on every swipe, and `AWARENESS WHY` always says what the post shows. A declared level holds exactly as before; where the post reads at another level, `AWARENESS WHY` says so in that same line, as a finding. No label, slot or rule changes. Everything in v13 stands.*
```

### awareness · change 2 of 2: read it off the post, and say what the post shows

**Before** (the block goes under this text of the base):

```
the source explains and what it assumes — but answer it for OUR reader, for
this exact desire, not for the source's. Then quote that level's `must_not`
verbatim from the slice, because every hook written downstream is checked
against it.
```

**After** (the text added):

```
**Read the level off the post itself, on every swipe (v15).** How
deeply the post describes the problem tells you the level. Ask it of every
swipe, whether or not a level was declared. Take the answer from the doctrine
read above and the teardown beat that shows it; never re-derive it.

`AWARENESS WHY` always says what the post itself shows: how deeply it
describes the problem, and the level that reads as. It says this as well as
what the rules above ask of it, and it stays one line.

A declared level still holds exactly as section 0 says: `AWARENESS:` and
`AWARENESS MUST NOT:` do not move. When the post reads at another level than
the declared one, `AWARENESS WHY` says so in the same line, as a finding:
`FINDING: the post reads <level>, declared <level>`. A finding is printed and
nothing more: it changes no label and stops nothing.
```

## creator-brief — 5 · the brief, creator lane

- **Fills:** 4.10 A creator's or founder's brief
- **Base:** `components/video-writing/prompts/stage-5-brief/creator-lane/stage5-creator-brief-v36-owner.md`
- **Out:** `components/video-writing/prompts/stage-5-brief/creator-lane/proposed/stage5-creator-brief-v37-owner.md`
- **New slots:** `{declared_layers}`
- **Applies to the other base:** n/a — no other base was named for this item
- **Also checked:** `components/video-writing/prompts/stage-5-brief/creator-lane/stage5-creator-brief-v35-owner.md` — applies (version note and 3 block(s) placed, every anchor found once)
- **Also checked:** `components/video-writing/prompts/stage-5-brief/creator-lane/proposed/stage5-creator-brief-v36-owner.md` — applies (version note and 3 block(s) placed, every anchor found once)
- **Where the words come from:** Decision 4.10 fill, sentence for sentence. 'The product facts' and 'the ask' are on the fixed list because the base already locks them (WHAT AMPLIFICATION MEANS HERE; THE LANE's ask, word for word); the fill itself fixes the angle and the key points. The hook lines under test are not put on the fixed list: the fill does not put them there.

### creator-brief · change 1 of 4: version note

**Before** (the note goes above the base's first line):

```
<!-- v36 (2026-11-16, V57 — the swipe is the backbone; everything on it is ours): every frame does the job of the source shot it stands on, in the source's order; the place, the action, how many frames, the outfits and the words on screen are ours, built from  [... the line goes on]
```

**After** (the text added):

```
<!-- v37 (2026-11-18, held for review, not live: it sits in proposed/, which the picker does not read; fills decision 4.10 of the video decision logic): the brief is handed the format by name, with the reason it was called that, in one new slot, `declared_layers`, and names it in its header; and it says which parts are fixed (the angle, the key points, the product facts, the ask) and which are the creator's own (the words, the slang, the delivery). The script stays whole and every labelled line is as v36. -->
```

### creator-brief · change 2 of 4: the format this is made in

**Before** (the block goes above this text of the base):

```
## THE LANE — paid or organic, and it changes only the ask (2026-10-21)
```

**After** (the text added):

```
## THE FORMAT THIS IS MADE IN (v37)

The teardown already decided what this video is: its format, its style, its
structure and how it is made, each with the reason it was called that.

{declared_layers}

Name the format in the brief's header, the way it is named above (the shape
below shows the line).
```

### creator-brief · change 3 of 4: the format, named in the header

**Before** (the block goes under this text of the base):

```
⟨One to three sentences: the core idea this concept runs on, from its own
material.⟩
```

**After** (the text added):

```
Format: ⟨the format this is made in — its id and its name, as THE FORMAT THIS IS MADE IN gives them⟩
```

### creator-brief · change 4 of 4: what is fixed, and what is the creator's

**Before** (the block goes above this text of the base):

```
# WHAT DOES NOT GO IN
```

**After** (the text added):

```
# WHAT IS FIXED, AND WHAT IS THE CREATOR'S (v37)

A brief that is too exact reads as an ad. So the brief fixes the angle and the
key points, and leaves the words, the slang and the delivery to the person
filming.

Last in each concept, after HOW IT LIVES ON CAMERA where it is printed, print
`## WHAT IS FIXED, WHAT IS YOURS` and five short lines, written to the
creator, plainly:

- **Fixed — the angle:** what this video argues, in one plain line.
- **Fixed — the key points:** what has to come across, in the script's order,
  a few words each.
- **Fixed — the product facts:** said as the script has them.
- **Fixed — the ask:** the last line, word for word.
- **Yours — the words, the slang and the delivery:** the `Say:` lines show one
  way to say it.

The script stays in the brief, whole: every `Say:` line is still written word
for word as the rules above say, and no frame, line or labelled line changes.
This section only tells the creator which parts hold and which are theirs.
```

## format-call — 0 · triage: the call on a format the lists do not know

- **Fills:** 3.3 A format the lists do not know
- **Base:** none (new file)
- **Out:** `components/video-teardown/prompts/proposed/format-call-guidance-v1-owner.md`
- **New slots:** none
- **Applies to the other base:** n/a — no base prompt: this file is new
- **Where the words come from:** Decision 3.3 fill only. The three choices are the ones the code takes today (fold, own, drop); each line says when to choose it and nothing about what it does to the run.

### format-call · change 1 of 1: the whole file (new)

**Before** (what exists today: there is no file):

```
nothing is shown
```

**After** (the text added):

```
<!-- format-call-guidance-v1 (2026-11-18, held for review, not live: shown nowhere yet; fills decision 3.3 of the video decision logic). The short guidance for the person deciding on a format the lists do not know. -->
# A format the lists do not know — how to decide

The run stops on a new format name until you decide. Decide by the structure:

- The same structure with our language swapped in is the same format, whatever it sells.
- Name a format by its structure.
- One that keeps winning is a format. One that won once is a one-off.

## The three choices

- **Same as X** — choose it when this has the structure of a format already on the list, with other language in it or another thing being sold.
- **Its own format** — choose it when the structure is on no list and it keeps winning. Name it by its structure.
- **Not a format** — choose it when it won once. It is a one-off.
```

## scratch-picks — 2 · an idea with no swipe: the picks before a from-scratch run

- **Fills:** 2.4 An idea with no swipe: format, style, arc
- **Base:** none (new file)
- **Out:** `components/video-writing/prompts/proposed/stage2s-scratch-picks-v1-owner.md`
- **New slots:** `{angles}`, `{avatar}`, `{awareness_levels}`, `{formats}`, `{language}`
- **Applies to the other base:** n/a — no base prompt: this file is new
- **Where the words come from:** Decision 2.4 fill for the order and the reason the format comes second. The fill gives no rule for the style or the arc and no list for either is among the slots this prompt may ask for, so both lines are plain words or 'not on file', never an id. 'A proposed default is not proof' is the line's own rule today (the decision's chain text).

### scratch-picks · change 1 of 1: the whole file (new)

**Before** (what exists today: there is no file):

```
the session picks by hand; nothing states the order or asks for a reason
```

**After** (the text added):

````
<!-- stage2s-scratch-picks-v1 (2026-11-18, held for review, not live: a new prompt, wired to no run; fills decision 2.4 of the video decision logic). For an idea with no swipe: the order the picks are made in, with one reason line for each. It makes picks only; it writes no script. -->
# An idea with no swipe — the picks, in order

There is no swipe for this run. Nothing was torn down, so nothing hands you a
format, a style or an arc. You make the picks a from-scratch run starts from,
in the order below, with one reason line for each. You write no script and no
brief.

## What you are given

The avatar: {avatar}

The brand's angle list, each angle with its id, its name and the one sentence
it argues: {angles}

Real language selected for this avatar, each row with its source: {language}

The five awareness levels, each with where the ad may begin: {awareness_levels}

The format list, each format with its id and what it is: {formats}

## The order

**Work the avatar side first: the angle, the language, the tone.** Then pick
the format.

1. **The angle.** One id from the angle list.
2. **The language.** The customer's own words the ad is written in, quoted
   from the rows above.
3. **The tone.** How it has to sound to this avatar, in a few words.
4. **The awareness level the ad enters at.** One of the five levels, by its
   id.
5. **The format.** Pick the format this avatar already watches, by the
   awareness level the ad enters at. One id from the format list. The format
   supplies the hook, the scroll stopper and the lead, so this step picks
   none of those three.
6. **The style and the arc.** They come last, after the format. This step is
   handed no list for either, so name each in plain words, or write `not on
   file`. Never coin an id.

Every pick comes from what you were given. Where the inputs do not show what
this avatar watches, say so in `FORMAT WHY`, and never present a guess as
what they watch. A pick made here is a proposal: a proposed default is not
proof.

## What you hand on, exactly in this shape

Eight labelled lines, in this order, one per line, spelled exactly this way:

```
AVATAR ANGLE: <angle id> — <one line: why this angle for this avatar>
LANGUAGE: "<the customer's words>" (<source>) ; … — <one line: why these>
TONE: <a few words> — <one line: what in the avatar's language shows it>
AWARENESS: <level id> — <one line: why the ad enters there>
FORMAT: <format id>
FORMAT WHY: <one line: what shows this avatar already watches it, and why it fits the level the ad enters at>
STYLE: <the look, in plain words — or not on file> — <one line: what it follows from>
ARC: <the order it is told in, in plain words — or not on file> — <one line: what it follows from>
```

Nothing else. No script, no hook, no scroll stopper and no lead.
````

## creator-page — 7b · the creator page

- **Fills:** 4.10
- **Out:** `components/video-writing/prompts/stage-7b-page/proposed/stage7b-concept-v11-owner.md` (saved as 61d0b1cff6)
- **Already stood:** keep the direction, the hooks and the angle and make it yours; their own words and style; hooks are directions; product points theirs to choose.

**Before:**

```
**The creator is a professional.** ... They take
it from there, in their own words and their own style. The spec's detail is for
our editor and our pictures, not for them.
```

**After (added):**

```
**What is fixed and what is theirs (v11).** Fix the angle and the key points: the direction the hooks take, the beats that must happen, the product points and the product's real facts. Leave the words, the slang and the delivery to the creator. A brief that is too exact reads as an ad.

+ slot line: Here is the format this video is made in, each layer with why it was called that: {declared_layers}

+ rule: ## The format line names the format (v11): the Format line uses that format's plain name in its three to six words; only the name goes on the page, never the playbook, beats or reasons; no format named = written from the spec as before.
```
