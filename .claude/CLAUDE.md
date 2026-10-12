# Prizm Lab — instructions for Claude

This repo is a public toolkit. People copy it into their **own private repo**
and run it there with their **own keys**. The person you're talking to is
probably not technical: do files, commands and checks yourself, silently, and
talk in plain words. Never ask them to run a command.

## Hard rules

- **Never commit `.env`**, and never print, echo, log or repeat a key value —
  not in chat, not in a file, not in a commit message.
- Never ask the person to paste a key into the chat. Open `.env` for them and
  let them paste it there.
- Brand information never goes into `daemnapps/prizm-labs` itself (the public
  original). It lives only in the person's own copy.

## "activate Prizm Lab"

When the person says **activate Prizm Lab** (or **continue onboarding**):

1. **Check the basics, silently.** `python3 --version` (3.9 or newer). If it's
   missing, tell them in one line what to install and stop there.
2. **Keys file.** If `.env` doesn't exist, copy `.env.example` to `.env`.
   Confirm `git check-ignore .env` says it's ignored. Don't ask for any key yet.
3. **Their brand folder.** Ask for the brand name (first checklist item), make
   a folder name from it (lower-case, dashes), and copy `brands/_TEMPLATE/` to
   `brands/<brand>/` if it doesn't exist yet.
4. **Let their copy save the brand folder.** Only if `git remote get-url origin`
   is **not** `daemnapps/prizm-labs` and the repo is private
   (`gh repo view --json visibility` says PRIVATE, when `gh` is available):
   add the line `!brands/<brand>/` right after `brands/*/` in `.gitignore`.
   Otherwise leave `.gitignore` alone and tell them their brand folder is only
   on this computer until they're in their own private copy.
5. **Walk the checklist** in `brands/_TEMPLATE/onboarding.json`, in order,
   **one item at a time**:
   - Progress lives in `brands/<brand>/onboarding-progress.json`
     (`done`, `skipped`). "continue onboarding" starts at the first item that
     is in neither list.
   - For each item: say what it is and why in one plain line, then ask the
     item's `ask` question. Where the item has `claude_can_fetch`, fetch it
     yourself from their website / reviews first and ask them only to confirm
     or correct.
   - Write what you learn into the item's `fills` files (keep each template
     file's shape; replace the `<placeholders>`). Mark anything you inferred
     as a draft for them to confirm.
   - Tick it: add the id to `done` (or `skipped` if they say "not now" on an
     optional item), tick the same box in `brands/<brand>/ONBOARDING.md`, and
     say what's left: "4 of 23 done — next: your best seller."
   - They can stop at any point. Nothing is lost.
6. **Keys come just in time.** Items with `"when": "just_in_time"` are not
   asked during the walk. Right before a tool runs, read the "Keys this tool
   needs" line in that tool's README; for each key missing (check with
   `python3 components/keys/loader.py NAME` — prints set/missing, never a
   value), tell them in one line what it's for and where to get it (from
   `.env.example`), open `.env` for them, and wait for them to say it's in.
7. **Self-checks.** After keys are in, run the tool's own check if it has one
   (`tools/video-teardown/machine/doctor.py`, `tools/email-production/doctor.py`)
   and report the outcome in one line.
8. **First run** (last item): run the first teardown on one of their swipes
   and show them the result.

## Where things are

- `START-HERE.md` — the four steps a person reads. (These instructions live in `.claude/CLAUDE.md`.)
- `.env.example` — every key name the tools read, what it's for, where to get it.
- `components/keys/loader.py` — how every tool finds a key: the environment,
  then `.env`, then (only on the original owner's Mac) his personal key store.
- `brands/_TEMPLATE/` — the brand folder every brand copies;
  `ONBOARDING.md` / `onboarding.json` are the checklist.
- Each tool's `README.md` says what it does and which keys it needs.
