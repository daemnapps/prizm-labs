<!-- writing v2 (2026-11-07, round 3, enrichment only): v1 copied whole, every line kept byte for byte; THE CUT ORDER is an addition that runs only when an audit fix asks for time back, so a fix that adds time and asks only for the change to be reported is made as written and nothing else is cut. -->
<!-- writing v2 (2026-11-07, fix round): the length call goes back to the owner as a question, never auto-held; the swipe's own words and a bank row's words are never cut; an approximate plan ("~46") is met when the time rounds to it; the worked example is a made-up product, not a test swipe. -->
<!-- writing v2 (2026-11-07): pass B PATCH v2 = v1 + THE CUT ORDER: when the script runs past its plan, time is taken back in one fixed order, and the payoff's set-up, the payoff, its verdict line and the closing ask are never cut. Adapted from zenstory/drama-skills (MIT): skills/short-drama-write/references/script-craft.md §9.10 Economy pass (SCR-23), skills/short-drama-write/SKILL.md (the compress order) and skills/short-drama-develop/references/episode-design.md §9.2. Bake-off candidate; v1 stays live until the owner picks. Every other rule and the output format of v1 stand, word for word. -->
<!-- writing v2 (2026-10-21): pass B PATCH v1 — the audit's RE-RUN BUILD answered by a patch, not a rebuild (video-system sync W32). The same full audit reads the patched script afterwards; nothing here judges. -->

# Writing v2 · pass B — the patch the audit asked for

The audit read the script below and sent it back with numbered fixes. Make **exactly those fixes and
nothing else**. Every line the audit did not name stays byte for byte as it is — the words, the order,
the markers, the tables, the part headers. You are not rewriting the script; you are correcting the
lines the audit pointed at. The same full audit reads the result again afterwards.
One addition to that: when an audit fix asks for time back, take it in THE CUT ORDER below.

Here is the script as it stands — the build pass's whole answer, its three parts marked
`=== PART n: NAME ===`:

{build_output}

Here is the audit's verdict and its numbered fixes, in its own words:

{audit_fixes}

Here is THE LANE this piece runs on — it changes only the ask:

{ask_lane}

## How to answer

For each fix, print one block, in the order the audit numbered them:

```
=== FIX <the audit's number or label> ===
PART: <PLACEMENT · EXPANSION · CLOSE — the part the lines are in>
FIND:
<the exact lines to change, copied character for character from the script above — enough whole lines
that they appear ONCE in the script>
REPLACE:
<the corrected lines>
=== END ===
```

Rules:

1. **FIND is a copy, never a paraphrase.** Copy whole lines out of the script exactly, spacing and
   punctuation included. A FIND that does not appear in the script, or appears more than once, makes the
   machine throw the whole patch away and rebuild the pass instead.
2. **REPLACE changes only what the fix names.** Keep everything else in those lines as it was.
3. **One fix may need several blocks** (the same mistake in two places): give each its own block, with the
   same number.
4. **A fix that needs a fact the files do not hold** is written as a `[RESEARCH: what is needed]` marker in
   REPLACE, exactly as the build pass would write it — never an invented number, name or price.
5. **Every rule of the build pass still holds** for the lines you change: the swipe's structure, the
   lane's last ask, every rung carries the product, claims only from the brand files.
6. Print the blocks and nothing else — no commentary before or after them.
7. **When an audit fix asks for time back, take it in THE CUT ORDER below** — and only then. The cuts
   stay inside the script, part or phase that fix names.

## THE CUT ORDER — when an audit fix asks for time back

**When it applies.** Only when a fix from the audit asks for time back: it names the script, a part or a
phase as running past its plan or its maximum and asks for it to be shortened. A fix that adds time and
asks only for the change to be reported ("Report the runtime change") is made as written; nothing else
is cut, and the length lines change only as that fix says. A script that runs long when no fix asks for
time back is left as the fixes make it: the same full audit reads it again. A script inside its plan is
never trimmed, and nothing is cut to "tighten" it. A plan
written as approximate ("~46", "about 46") is met by any time that rounds to it at the same precision:
46.4s is inside "~46".

**Never cut.** These carry the piece; whatever else happens, they stay word for word:

1. The opening: the hook lines and the first shot.
2. The payoff and the three lines that frame it. The payoff is the beat the piece builds to: the proof
   or the result shown. Its **set-up** is the line that makes the viewer wait for it (the doubt the proof
   answers). Its **verdict line** comes right after it and says what the payoff means. The **closing
   action** is the last ask. The verdict line is never "one more line after the payoff": it is the
   settlement the set-up promised.
3. Any line a brand file or a binding rule requires (name the file), and every claim, number, product
   name, mechanism step, offer term and the guarantee sentence. A claim said twice is still one claim:
   step 1 below keeps one statement of it.
4. The swipe's own words, in any row, `[SOURCE]` or `[ADDED]`: its connectives and turn words too
   ("See,", "Now", "But", "So"). Check a word against the swipe's transcript before you cut it. A
   `[SOURCE]` line also stays as a line: the swipe's beat count stays.
5. A language-bank row's words. When a line quotes a row (its id is in the script's source table), the
   row's phrase stays whole: never cut part of a customer's or a prospect's words.
6. Filmed words.

**Cut in this order, and stop as soon as the part the fix names is back at or under its limit.** Cut the
fewest pieces that get it there; take a later step only when the earlier ones have nothing left. Every
step cuts only words this pass or an earlier pass wrote, never words the list above protects.

1. **Repeats.** The same fact said twice in our words. Keep the fuller statement, or the one closer to
   its proof; cut the other.
2. **Explanations.** A line or phrase that explains what the viewer already sees or was already told,
   and a second or third proof stacked on one conclusion. Keep the strongest proof.
3. **Same-direction lines after the payoff.** One more decision, explanation or consequence pointing the
   way the verdict line already points — unless a protection above covers it.
4. **Transitions we wrote** that only move the viewer from one place to another and carry no fact or
   choice.
5. **Inside a protected line,** only a phrase of our own words it says twice, keeping the one phrase the
   set-up points to.

**What goes back to the owner.** The length call is the owner's. When a fix asked for time back and the
part it names still runs past its limit after the cuts above (or when nothing could be cut), write
the length flag as a question, never as a decision: what runs over and by how much, which protection
keeps each line in that part, and the owner's options in plain words (accept the longer part, or drop a
named line). Never write that the overrun is held, accepted or approved.

**How a cut is written.**

- Label each cut block `=== FIX <n> · TRIM ===`, where `<n>` is the audit fix that asked for time back.
- Time a cut at the speaker's pace in that beat: the beat's words divided by its seconds.
- Retime everything after the cut: every later row of the script table, the captions row, every
  on-screen row with a time, and the `Runtimes` line (say which fix added time and which cut took it
  back). Consecutive rows may share one block. Move only this script's own times: a time cited as a
  receipt (a moment in the swipe or in a winning ad, such as "WINNER-CORE01 0:09.0") stays as it is.
- Never leave REPLACE empty. To cut a whole row, FIND it together with the row after it, and REPLACE with
  that next row alone, retimed.
- Update the FLAGS line about length, if there is one, under the rule above: a question for the owner
  while anything still runs over.

**An example** (made up: a made-up drink bottle and made-up lines, to show the order; it is no real
run). The plan is 30.0s. Audit fix 2 adds a 1.0s hold on the proof, so "this script" runs 31.2s and
the close runs 1.5s past its 4s maximum. Audit fix 3 asks for the script to be brought back to its plan
and the close to its maximum.

- Protected: the swipe's "Now" at the turn, the customer row "keeps it cold all day" (bank id in the
  source table), the set-up "Does it really stay cold?", the proof shot, the verdict line "That's why
  we guarantee it.", and the ask.
- Step 1 finds a repeat in our words: beat 4 says "it stays ice cold for hours", and beat 7 already says
  "cold from morning to night", the fuller statement. "for hours" is cut: 2 words, 0.5s at that beat's
  4 words a second. Step 4 finds the joining phrase we wrote, "and here's the thing,": 0.8s. The script
  runs 29.9s, inside the plan.
- The close is still 1.5s past its maximum, and every line in it is protected. The flag reads: *"The
  close runs about 1.5s past its 4s maximum: the set-up, the proof hold (fix 2), the verdict line and
  the ask are all protected, so nothing in it was cut. The piece runs 29.9s, inside the plan's 30.0s,
  after two cuts upstream. The owner decides whether to accept the longer close or drop the proof hold."*

**Banned in a cut.** Cutting the hook, the set-up, the payoff, the verdict line, the closing ask, a
required line, a fact, a swipe word or part of a bank row. Trimming a script that is inside its plan.
Speeding a line up or leaving the timings unchanged so the sum looks right. Writing the length call as
made: "held", "accepted", "ships at".
