# <Brand> — the story

**The storytelling framework. `position.md` says what we claim; this file says
who tells it, and what happens to them.** Every video ad, and in time every
page, email and static, is one of the stories below told by one of the tellers
below. A story that isn't here doesn't run until it is added here with a
receipt.

_Started by <name>, <date>, off <the swipe, ruling or run that started it>.
Nothing below is invented. Every story is assembled from what the brand has
already ruled or what a customer already said, and each one names its receipt.
A slot the evidence cannot settle says `open`, and open slots are the owner's._

---

## The story block

_The block the machines read, bound as `{story}`. Fifteen slots, this order,
these labels, one per line, no blank lines inside the fence. A slot the file
cannot settle says `open`. Add `confirmed by: <your name>` to lock it. Until
then a stage prints its own read beside this one and flags any disagreement
rather than resolving it. **Lane: <the lane this block serves, and its
channel — or "the only lane">.** `components/marketing-doctrine/lint_story.py`
refuses a file that drifts from this shape._

```
SPINE: <before → turn → after, one short clause each, in the reader's register>
BEFORE: <what the reader did to live with the problem — the behaviour, not the feeling>
TURN: <the moment the cause gets renamed — position.md → MECHANISM, told as something found, never as a lecture>
AFTER: <what someone else sees or says now, or what the reader does again that they had stopped doing>
TELLERS: <numbered, " · " between them: the reader themselves first, then the authority role from position.md → AUTHORITY, then any other receipted teller>
ENTRY: <how a story is opened in the reader's own words — cite the language rules' Story Entry Points, or `open` where the bank has none>
STORIES: <the story ids, " · " between them, each one a `###` below; a story still missing a receipt is marked "(open)">
ARC: <the doctrine's story-testimonial frame, by name and path — this block is what the brand puts in each phase>
REASON TO SWITCH: <position.md → DISPLACES, told as what the reader tried themselves and why none of it could reach the cause>
OPENS IN: <the moments the reader already buys in, from the avatar's own moments and buying times>
PRODUCT ENTERS: <where the product enters the story — at the turn, never the first line — and how many offers>
PROOF: <what counts as proof, shown not claimed — from the language rules' proof hierarchy>
VOICE: <whose words, which register, and the register it never uses>
NEVER: <an invented customer · an invented number · a real customer's face generated · plus the brand's own never-list items that bite on a story>
confirmed by: open
```

---

## The lesson this file comes from

<The swipe or ruling this file was started from, in two or three lines: what
the brand behind it keeps fixed, and what it rotates.> Mapped onto us:

| They do | We do |
|---|---|
| The product line never changes | `position.md` → LINE and SPINE never change |
| A named person with their own reason | A **teller** from the list above, telling one of the **stories** below |
| The villain rotates | <what the reader already tried rotates — from DISPLACES> |
| Each story aimed at a buyer with intent | Each story opens in a moment the reader already buys in (OPENS IN) |
| Proof is the person, not a counter | <what proof is here, from PROOF> |
| <their weak spot> | <how this brand builds depth instead> |

## The stories

<How many stories, for which lane. Each one is the SPINE told from a different
door. The beats are the order a video runs in; a static or an email uses the
same beats compressed.>

### <story-id> — "<the verbatim line the story is named for, or a plain line naming it>"

- **Beats:** <beat → beat → beat → the turn → the after, in the order a video runs>
- **Why it works:** <one or two lines, citing position.md or the avatar file>
- **Teller:** <one teller from TELLERS>
- **Fits:** <the sub-avatar ids it fits, by file stem>
- **Receipts:** <"verbatim" (source file, who said it and where) — every quote exact, every one resolvable>
- **Open:** <optional — what this story still needs, and whose call it is>

## The tellers

Casting comes from `identity-anchors.md` and the rights positions there
override anything here.

| Teller | Cast from | Rule |
|---|---|---|
| <the reader themselves> | <where their footage or casting comes from> | <the rule that binds it> |
| <the authority role> | <cast from> | <rule> |

## The <second lane> lane — a separate block

_Optional. Only when the brand declares a second lane that is never blended with
the first. Same slot labels, a subset, same order, `confirmed by:` last. Delete
this section otherwise._

```
SPINE: <the second lane's spine>
STORIES: <its story ids, or `open`>
confirmed by: open
```

## How a run uses this

1. The run declares its lane and sub-avatar, as it does today.
2. It picks **one story** from STORIES that lists that sub under **Fits**, and
   **one teller** from that story.
3. Hook, script and brief follow that story's **beats**. The opening lands in
   one of the OPENS IN moments. The product enters at the turn.
4. The story's name is recorded on the run next to the angle and format, so the
   story that wins can be read off results the way angles are.

## Where it lives in the chains

`{story}` is bound the same way `{position}` was: one line per stage in the
chain config, a new version of each prompt that reads it, a row in the
variables reference, and this template plus its lint so every brand's file has
the same shape. **The generic arc stays in the doctrine**
(`story-testimonial` in `components/marketing-doctrine/ad-frameworks.json`,
`storyteller` in `delivery.json`). **This file only carries what the brand puts
into it.** It **references** `position.md` (DISPLACES, AUTHORITY, TRUST MOVE)
and never restates it, so the brand facts live in one place.

<Per chain that reads `{story}`: which stages read it and what each does with it.>

## Receipts

- The position, the words, the binding rules — `position.md`
- <the avatar file>
- <the language bank, with its row count>
- <the sub-avatars and their one-line stories>
- <casting and rights — `identity-anchors.md`>
- The generic story arc and the storyteller delivery — `components/marketing-doctrine/ad-frameworks.json` (`story-testimonial`), `delivery.json` (`storyteller`)

## Open

- **The block is declared, not confirmed.** Nothing locks until `confirmed by:` names a person.
- **Which story wins is unmeasured** until story names are recorded on runs.
- <Each other `open` slot or story, and what would close it.>
