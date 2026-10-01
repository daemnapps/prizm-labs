# How to run a teardown — one way

You work inside **Higgsfield Supercomputer** with this repo cloned into it.
(Claude Code with the repo cloned works the same way.) You do not paste files
into a chat, you do not copy anything into a Drive, you do not install
anything. You say what you want and it runs the chain.

---

## Once — clone the repo (two minutes)

1. In Supercomputer: **Connectors → Explore** → connect **GitHub** and
   **Google Drive**.
2. New chat → paste `https://github.com/daemnapps/prizm-labs` and say
   **"clone this"**.
3. Any time after: **"pull my GitHub repository and look for updates."**
   That is the whole update process.

## Once per brand — fill in the brand folder (one afternoon)

Say: **"Copy brands/_TEMPLATE to brands/<my brand> and walk me through
filling it in."** It asks you the questions in the template's README, in
order, and writes your answers into the files. Every tool reads this folder,
so you explain your brand once.

**The one people skip, and regret:** the product document. Describe the
product the way a camera sees it — the container, the colour, the finish,
every word printed on the label. Skip it and every image you generate shows
a product that is not yours.

## Every video — the teardown

Say: **"Tear down this video for <my brand>"** and give it the video — a
link, or a file you drop in.

It runs `the-chain/` in order and stops to show you at each step:

1. **Watch** — it watches the video and writes the scene record: what is on
   screen, what is said, what is printed, when.
2. **Tear down** — the structure underneath: the beats, the hook, the proof,
   the close. What earned the views, separated from what was sold.
3. **Spec** — the video described as something rebuildable, with the
   brand-specific parts pulled out and left blank.
4. **Inject** — your brand folder goes into the blanks: your customer, your
   words, your product where theirs was. Anything the folder does not say,
   it flags as *not known* rather than inventing.
5. **Hooks and brief** — the hook options, then the brief: the scenes, what
   is said, what the person wears, and a prompt for every frame.

The brief is written to `brands/<my brand>/briefs/` — and, when Drive is
connected, to the brand's `briefs/` folder on Drive, where it shows on the
queue for whoever makes the video (`tools/editor-onboarding`).

## Then — the scenes

Say: **"Make the scenes for this brief."** `tools/video-production`
takes it from here: stills, motion, voice, the editor pack. The models and
settings it uses are in `WHICH-MODELS.md` — it does not leave anything on
Auto.

Two things decide whether it looks real, and the chain enforces both:

- **Every blank is filled from the brand folder.** `{PRODUCT}`, `{SUBJECT}`
  are questions, not decoration. Nothing is guessed.
- **Every person and product carries its reference in every frame.** That is
  how the same human appears in every shot.

## When it goes wrong

**"It made up a product that isn't mine."** The product document is missing
or thin. Describe the packaging properly, then say "regenerate".

**"The script doesn't sound like my customer."** The language file needs
more real sentences — reviews, comments, tickets, copied exactly.

**"It says it doesn't know something."** Correct behaviour. It is telling
you which part of the brand folder is empty. Fill that part in.

**"The scenes don't match each other."** A reference was missing on a frame.
Say which scene; it regenerates from the cast sheet.

## What good looks like

Hand the finished brief to someone who has never seen your brand. If they
can make the video without asking you a single question, it worked. If they
have to interpret anything, go back and make that part specific.
