# Video Teardown

Take any video that already worked — a competitor's ad, an organic post, a
creator video someone sent you — and get back a finished brief for **your**
brand: the scenes, what is said, what people wear, the hooks, and a prompt
for every shot you need to make.

Nothing gets installed. Nothing runs on your computer.

## What you need

1. **Higgsfield Supercomputer** with this repo cloned into it — where the
   video gets watched, the chain runs, and your scenes get made. Claude Code
   with the repo cloned works the same way.
2. **Your brand folder** — `brands/_TEMPLATE/`, copied to `brands/<your
   brand>/` and filled in once. Say "walk me through it" and it does.

## Start here

**Read `HOW-TO-RUN-IT.md`.** Clone once, fill the brand folder once, then
"tear down this video for <brand>". Everything else in this folder is what
the chain runs.

## What is in this folder

- `HOW-TO-RUN-IT.md` — the one way to run it. Start here.
- `WHICH-MODELS.md` — the exact models and settings to use. Do not leave it
  on Auto; this names what actually works and what to do when a shot looks
  wrong.
- `the-chain/` — the prompts the chain runs, one file per step, numbered in
  the order they run. Read them to see how a brief is made; edit them to
  change how every brief after is made.
- `reference--the-automated-version.md` — ignore this one unless you have a
  developer. It describes a version that runs the whole thing unattended.

## The two rules

**Rebuild the structure, not the content.** The shape is what earned the
views. Your product is what changes. A scalp treatment and a countertop demo
can be the same format — that is the point.

**Nothing invented.** If your brand folder does not say what your product
looks like or what your customer sounds like, the tools will tell you they do
not know rather than make something up. That is them working correctly. Go
fill in that part.

---

*Prizm Labs — daemn.co. Free, MIT licensed.*
