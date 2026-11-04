# How we build an ad body

the owner, 2026-10-23: "I never really created a process to create bodies for ads. We've only
just done teardowns and swiping … not sitting down and actually building out direct
response bodies that can just work with any type of hook."

A **body** is everything after the hook: the part that sells. It is stitched behind a
hook we test separately, so it has to stand on its own. First built with the pastor barber
body (`runs/video-writing/<brand>/pastor-barber-body/BODY-owner.md`; page:
(private page)), and shaped by the owner's Tella review of
the old cut ("Ad Editing Review and Feedback", 2026-10-23).

**What went wrong before.** The three barber bodies (guy, baddie, pastor) came out of
`machine/presenter_body.py` (stage 3p) and straight into production. the owner's review: the
script was good; the scenes were "cut, paste, cut, paste" with no arc, the presenter sat in
one barbershop set, no B-roll showed what he was saying, the voice was awkward and
breathy, and the edit had dead pauses, late audio and a presenter outside the safe zone.
"We jumped the gun." The swipe had never been studied shot by shot before scenes were made.

## The steps

1. **Study the swipe shot by shot.** From its teardown: its sets, its camera angles, what
   the presenter does on every line, where the crowd or reaction shots cut in, the props in
   every shot, the music bed, how it ends. Write it down as a table before writing scenes.
2. **Write the selling script.** Call-out → agitate → the turn (the brand's mechanism) →
   why the old fix misses → the answer → demo → proof → offer → call to action. Only claims
   already in the brand's product, offer and rulings files; an open claim stays out until
   the owner rules on it.
3. **Line one stands alone.** The body works with nothing in front of it. Each hook gets
   its own one-line lead-in (for the fight: "Put the brush DOWN! Both of y'all… come to the
   chair!"), made as its own small shot, so hooks swap without touching the body.
4. **Give every line a scene.** A few sets from the swipe's world, not one set for the
   whole body; one start picture per set (VIDEO-RULINGS V35 (set-ups not lines)). The
   presenter does something on every line. If he is flying, he talks while flying.
5. **Mark every moment before anything is made** (the owner, 2026-10-23: "we need clear discernment on A-roll, B-roll inserts, sound effects … there's no reason unless called for in the scene to have generated that"). Each moment is one of: a talking clip (A-roll), a B-roll insert, a voice over a shot that already exists, or a sound effect. Only the first two are generated. A one-word reply ("…Amen.", "…No.") is a voice over the shot we already have, never its own clip.
6. **Give every claim its B-roll.** He says peeling, we see peeling. Product on skin and
   before/afters are real footage (V36 (real product footage)).
7. **the owner signs off the script and the scene map** on the body's page. Nothing is made
   before this. The swipe's bits that are not in the script yet are offered as optional
   adds for him to pick.
8. **Voice: a clean read.** No heavy breathing, no dead air between lines.
9. **Make it through the runner, never by hand** (2026-10-23). Production runs through `tools/video-production`'s
   runner, where the checks live; if the brief does not fit it, convert it or ask the owner. Every picture of a person passes
   the face gate (`machine/face_gate.py`) before any clip — on 23 Oct a hand-driven run skipped it and a different man
   played Marcus in four scenes.
10. **Make, then edit clean.** Brief with A-roll and B-roll separated
   (`tools/video-production/BRIEF-SPEC.md`), elements through
   `tools/video-production/machine/elements_check.py`, then a hand-off folder to the
   Hand-off Standard (`lab/owner/handoff-standard/HANDOFF-STANDARD.md`; worked example
   `runs/video-production/<brand>/freestyle-1022/handoff/`). In the edit: the presenter stays
   in the safe zone, no frozen frames between lines, every line starts on time.

## Checks on every body

- Length about 60–90 s (the pastor body went from 2:51 to ~85 s).
- Every shot ties to a line. No cutaway without a job.
- A reaction or a new set every 10–15 s.
- The product moment is the strongest moment.

## Next bodies on this process

The guy barber, the baddie barber, and bodies for hook-only pieces (the goat headbutt → NOVA hook).
