---
name: email-upload
description: Put a finished email into Klaviyo as a DRAFT — a finished email run goes in; a checked draft campaign comes out with its approval card, nothing scheduled or sent. Use whenever someone says "upload the <brand> email to Klaviyo", "put nov-02 in Klaviyo as a draft", "make the Klaviyo draft for <brand>", "check the email before it goes to Klaviyo", "dry run the klaviyo upload", "make the card for the draft that is already in Klaviyo", or names a finished email and Klaviyo.
---

# Email upload

> **Activates component:** `components/email-production` — `klaviyo_upload.py`, one command that checks a finished email and makes a Klaviyo DRAFT plus its approval card.

External dependencies: `components/email-production/klaviyo_upload.py` (the uploader), `components/email-production/simple_email.py` (its draft-creation calls), `brands/<brand>/email-sms/` (audience matrix and sending settings), the brand's Klaviyo key in the environment by name only.

This is the Klaviyo twin of `meta-upload`: it stops at a draft. A person approves and schedules.

## Always dry-run first

```
python3 components/email-production/klaviyo_upload.py --run runs/email-production/<brand>/<label> --dry-run
python3 components/email-production/klaviyo_upload.py --run runs/email-production/<brand>/<label>
python3 components/email-production/klaviyo_upload.py --run runs/email-production/<brand>/<label> --card
```

- `--dry-run` checks only. It talks to nothing and writes nothing. Show the person what it found.
- The real run creates a Klaviyo template and a DRAFT campaign. That reaches an outside service, so run it **only when the person has asked for the draft**, after the dry run passes.
- `--card` makes the approval card for a draft that is already in Klaviyo, after re-checking it.
- Flags: `--pick <n>` chooses the subject pair (0 is the main one); `--again` makes a second draft even though one exists (ask first).

## What it checks before anything leaves

The words, the chosen subject and preview, prices and the delivery gate, unfilled notes, the audience (the slot's segments resolved through the brand's audience matrix), the from-line and send hour, the hero picture, and every link in the finished HTML. Anything wrong means HELD: nothing goes to Klaviyo and every problem is listed. Fix what it names upstream and run again.

## Rules

1. **Never sends. Never schedules.** `--send` is always refused. Scheduling is a person's act (the owner's or an approver's), through the email approval step, with the send switch on and at least 30 minutes of lead time.
2. A draft goes to the send's own segment, never "all". Sends go to the Engaged segments.
3. A draft whose plan day has passed gets no card.
4. Never paste or open a key. If the Klaviyo key is missing, say which capability is missing and stop.
5. No brand names in the skill; brand facts come from `brands/<brand>/`, which is never written here.

## What comes back, and where it lands

The draft campaign in Klaviyo and, in `runs/email-production/<brand>/<label>/`: `klaviyo-status.json` (the small record), `email-card.json` and `email-card.html` (what Klaviyo holds, the checks and a fingerprint), and `deliverable/pushed.json` (the campaign id). Say plainly that nothing was scheduled or sent.

Reply with the result and the folder it landed in (repo path or Drive folder name).
