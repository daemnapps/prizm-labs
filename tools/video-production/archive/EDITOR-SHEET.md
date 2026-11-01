# The editor sheet — what to do with a submit folder

You'll get a folder. This page says what's in it and what to do with it —
nothing here assumes you've seen the rest of this repo.

## What you receive

- `SUBMIT.md` — the sheet itself. One block per shot, with the exact
  prompt and settings for that shot already written out.
- `media/` — a folder of stills, already made and approved.
- `voice/` — a folder of voice lines, already recorded.

## The five steps, in Higgsfield

1. **Upload the medias.** For each block on the sheet, upload the still it
   names from `media/`, and the voice line it names from `voice/`.
   Higgsfield gives each upload its own media id — write both ids down;
   you need them in step 4.
2. **Open the block's model.** The sheet names which model runs that
   block. Open that model in Higgsfield.
3. **Paste the prompt and the parameters exactly as the sheet has them.**
   Don't shorten anything, don't fix wording you don't like, don't add
   anything of your own.
4. **Attach the medias with the roles the sheet gives them** — the still
   as `start_image`, the voice line as `audio` — and for a talking beat,
   set the mode to `omni_reference`. That's what makes the mouth match
   the line, instead of just animating the picture.
5. **Submit the block**, then move to the next one.

## What to write back

One file, `results.json`, saved into the same folder you were given. One
row per block, with:

- `id` — the block's id, taken straight from the sheet
- `job id` — the job id Higgsfield gives you
- `output url` — the link to the finished clip
- `seconds` — how long the clip runs
- `status` — one of `done`, `nsfw`, `ip_detected`, or `failed`

A block that got blocked or refused still gets a row. Write down what
actually happened — don't leave it out because nothing came back.

The machine transcribes every clip and compares it to the line; a clip
that says other words comes back to you as FLAG, not as a note.

## Three rules

1. **Never change a prompt.** Not a word, not the order, not "cleaning it
   up." If a prompt reads wrong to you, flag it back — don't fix it
   yourself.
2. **A blocked job is written down as blocked, never re-tried twice on the
   same model.** One retry is fine if the first attempt looks like a
   fluke. A second block on the same model means stop and write the row
   as `nsfw` or `ip_detected` — not `failed`, and not a third attempt.
3. **Nothing gets re-rolled because it "could be better."** Re-rolls are
   decided from the QC verdicts after you hand results back, not from a
   feeling while you're sitting in Higgsfield.

---

Written from the exact call shapes proven in `higgsfield.md`: everything
except the medias goes inside `params`; `medias` is its own separate part
of the call, as a list of `{value: <media id>, role: <the role>}`.
