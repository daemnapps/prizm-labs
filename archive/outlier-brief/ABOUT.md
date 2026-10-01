# The Outlier Brief

The second door. The first door starts from somebody else's ad; this one starts
from **your idea**. You say it rough, the system rounds it out with everything
the brand has on file, and writes one concept brief. **You approve it.** Only
then does it name the formats it should be made in and write the hand-off for
each production chain. It never makes the asset.

`SPEC.md` is the spec (Damon's, settled 2026-09-20). `spec.html` / `page.py` are
its page. `CLAUDE.md` is how the tool is built and gated.

## The two commands

```
# 1 — the idea, up to the concept brief. Stops: awaiting approval.
python3 outlier-brief/tools/run.py <idea file, or "-" for piped text> --brand <brand>
        [--avatar A] [--sub S] [--angle ID] [--offer KEY] [--awareness LEVEL] [--sophistication STAGE]
        [--answers "text or file"] [--label L] [--dry-run] [--rerun-from idea1|idea2|idea3|idea4] [--model M]

# 2 — his verdict, then the formats and the hand-offs.
python3 outlier-brief/tools/approve.py <label> --brand <brand> [--note "..."]
        [--media video,image,copy,page,email] [--formats video:<format id>[+<style id>],…]
        [--route ai|creator|founder] [--product P] [--send-back] [--hand-off-only] [--dry-run]
```

In a worktree, set `AI_WORKSPACE=<that worktree>` on both.

| Half | Model calls | What you get |
|---|---|---|
| `run.py` | up to 4 (3 with awareness + sophistication pinned) | `deliverable/concept-brief.md` — the brief, your idea quoted back, and the questions the files could not answer |
| `approve.py` | 1 — or 0 with `--formats` | `formats.json`, `deliverable/handoff--video.json` + `.md`, and a `handoff--<medium>.md` for every other medium asked for |

Everything files to `runs/outlier-brief/<brand>/<label>/`.

## The idea file

A few sentences, as rough as you like. Anything inside `<!-- … -->` is a note
to people and is stripped before the idea is read. `examples/example-idea.md`
is an EXAMPLE, clearly marked, naming no real claim — replace it with a real
idea.

## What it reads

From `brands/<brand>/` only, at run time: the position, the stories, the offer
bank, the objection bank, the avatar's card, the angles, and the customer's own
words (through `components/language-layer`). From `components/marketing-doctrine`:
the rendered slices for mass desire, awareness, sophistication and the ad
frameworks. From `components/elements`: every format, style and framework list.

## Where each hand-off stands today

| Medium | Hand-off | The chain's door for a brief |
|---|---|---|
| **video** | `handoff--video.json` — the choice `compose.py` takes (brand · avatar · sub · awareness · sophistication · format · framework · route), plus the brief | **the choice is accepted today; the brief itself is not read yet.** `compose.py` has no slot for an idea (SPEC §1). The printed `plan` command makes no model call (it opens a run folder in the video chain and proves the choice resolves); the brief reaches the writer only once `compose.py` binds it — a change in `components/video-teardown`, outside this tool. |
| image | `handoff--image.md` | to build — the image chain only knows swipes |
| copy | `handoff--copy.md` | not proven — copy production takes a source file; the hand-off can be that file |
| page | `handoff--page.md` | to build — the pages chain starts from a captured page |
| email | `handoff--email.md` | close, not proven — email production takes a source and an argument |

Nothing is started by this tool. Each hand-off prints the command and files it.

## Not built yet (SPEC §6, in its order)

The grid (one idea × several awareness stages × several formats in one run),
the research gatherer's live rooms as an input, and the Control Room trigger.
One idea, one awareness entry, one brief — proven on a real idea first.

## Tests

```
python3 outlier-brief/tests/test_outlier_brief.py
```
