# Image Teardown

**Paste a picture ad. Get its structure and a brief for your brand.**

A picture ad is one image, or a carousel (many images you swipe).
This tool looks at the ad. It writes down how the ad is built.
Then it writes a brief: a plan to make the same kind of ad for your brand.

It does not make the picture. A designer, or Image Production, makes it
from the brief.

## What you need

1. **Higgsfield Supercomputer** or **Claude Code**, with this repo in it.
2. **Your brand folder.** Copy `brands/_TEMPLATE/` to `brands/<your brand>/`.
   Fill it in one time. Say "walk me through it" and it helps you.
   The tool needs three things from it: your **product**, your **customer**
   (who buys), and your **offer** (the price and the deal).

## How to use it

1. Paste the picture ad. (A carousel: paste all the pictures, in order.)
2. Say: **"tear down this picture ad for <your brand>"**.
3. Wait. It works step by step.
4. Read what you get back.

That is all. You do not type commands.

## What you get back

- **The structure.** What is in the ad: the words, the picture, the layout,
  the colors, the order your eye reads it. Nothing about its brand. Just the
  shape.
- **The labels.** What kind of ad it is, from a fixed list.
- **The brief.** The same shape, with your product, your customer and your
  offer inside it. Headlines to choose from. What the picture shows.

## Two kinds of brief

- **For the machine (AI)** — the default. A work order for a designer or for
  Image Production.
- **For a creator** — a person with a phone. Say "brief for a creator".
  One simple page: the shot, the words. Nothing technical.

## The steps it runs

Each step is one prompt in `prompts/`. You can read every one.

| Step | What it does |
|---|---|
| 1 | Looks at the ad and writes down everything in it |
| 2 | Takes the brand out. Keeps only the shape |
| 2b | Labels what kind of ad it is |
| 3 | Puts your brand into the shape |
| 4 | Writes headlines |
| 5 | Writes picture ideas |
| 6 | Writes the brief |

The newest version of each prompt is the one with the highest number
(`-v5-` is newer than `-v4-`).

## Two rules

**Keep the shape. Change the content.** The shape is why the ad worked.
Your product is what changes.

**Nothing made up.** If your brand folder does not say something, the tool
says "I don't know" and stops. That is correct. Go fill in that part of your
brand folder.

## When something goes wrong

- **"missing"** — a file in your brand folder is empty or not there. The
  message says which one. Fill it in.
- **"held"** — the tool checked its own work and found a problem (a wrong
  price, a gap). It says why. Fix that, then ask again.

## More

- `RUN.md` — how to run it by hand, with commands (for people who code).
- `CLAUDE.md` — the full definition.

---

*Prizm Labs — daemn.co. Internal system — not for sale.*
