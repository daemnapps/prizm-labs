# How to run a teardown — no technical anything

You need three things, all of which you already have or can get in five
minutes: **a video**, **Claude** (the chat, or Cowork), and **Higgsfield
Supercomputer**. Nothing gets installed. Nothing runs on your computer.

If you can save a file to Google Drive and paste text into a chat box, you
can do this.

---

## Before your first teardown — set up your brand folder (once)

Everything the machine writes about your brand comes from one folder in your
Google Drive. Fill it in once and never again.

1. In Google Drive, make a folder and name it after your brand.
2. Open the **brand folder kit** you downloaded and make one Google Doc for
   each file in it, keeping the names. You can copy the text of each straight
   into the Doc.
3. Fill them in. `README` in that kit tells you what each one is asking for
   and the order to do it in. It takes an afternoon and it is the whole game
   — every ad the system writes is only as specific as this folder.

**The one people skip, and regret:** the product document. Describe your
product the way a camera sees it — the container, the colour, the finish,
every word printed on the label. If you skip it, every image you generate
will show a product that is not yours.

---

## The teardown, step by step

### Step 1 — Get the video and let it be watched

Save the video you want to tear down to your Google Drive so you have it.

Then open **Higgsfield Supercomputer** and upload it there. Supercomputer has
a Gemini model on it, which can actually watch video — that is the piece a
chat window alone cannot do. Ask it:

> Watch this video and write down every scene: what is on screen, what is
> said out loud, any words that appear on screen, what the person is wearing,
> and roughly when each scene starts. Do not summarise it — I want a record.

Copy what it gives you. That is your **scene record**, and everything below
works from it.

### Step 2 — Tear it down

Open Claude. Start a new chat. Paste in, in this order:

1. The contents of `the-chain/stage-1-teardown.md`
2. Your scene record from step 1

Claude writes back the teardown: the structure underneath the video. Keep it.

### Step 3 — Turn it into a spec

Same chat. Paste in `the-chain/stage-2-replication.md`.

You get back a spec — the video described as something rebuildable, with the
brand-specific parts pulled out and left blank.

### Step 4 — Put your brand in

Same chat. Paste in `the-chain/stage-3-injection.md`, then attach or paste
your brand folder documents — the avatar, the language, the product, the
offers.

*(If you use Claude Cowork, connect your Google Drive and just point it at
your brand folder instead of pasting.)*

Now the spec becomes yours: your customer, your words, your product where
theirs was.

### Step 5 — Write the hooks and finish the script

Same chat, in this order: `the-chain/stage-4-loop.md`, then
`the-chain/stage-5-brief.md`.

What comes back is the brief — the scenes, what is said, what the person
wears, the hook options, and a prompt for every frame you need to make.

**Save the brief to your brand's folder in Drive.** That is the deliverable.
Anyone who makes videos for you can work from it.

### Step 6 — Make the scenes

Back in **Higgsfield Supercomputer**. For each scene in the brief, paste its
image prompt in and generate the frame, then use the motion note to turn the
frame into a shot.

Two things that decide whether this looks real:

- **Fill in every blank.** The prompts have gaps in curly brackets like
  `{PRODUCT}` and `{SUBJECT}`. Those are questions, not decoration. Fill them
  from your brand folder — never let the model guess.
- **Keep people consistent.** Generate every scene of one person from the
  same starting frame, or they will be a different human in every shot.

### Step 7 — Cut it

The brief's scene list is the edit, in order. Cut the shots to it in whatever
editor you already use.

---

## When it goes wrong

**"It made up a product that isn't mine."** Your product document is missing
or thin. Go back and describe the packaging properly, then regenerate.

**"The script doesn't sound like my customer."** Your language file needs
more real sentences. Reviews, comments, tickets — real words people actually
wrote, copied exactly.

**"It says it doesn't know something."** That is correct behaviour, not a
bug. It is telling you which part of your brand folder is empty. Fill that
part in.

**"The scenes don't match each other."** You generated each one fresh instead
of from the same starting frame. Regenerate from one seed image.

---

## What good looks like

Hand the finished brief to someone who has never seen your brand. If they can
make the video without asking you a single question, it worked. If they have
to interpret anything, go back and make that part specific.
