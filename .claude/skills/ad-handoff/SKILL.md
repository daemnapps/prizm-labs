---
name: ad-handoff
description: Hand a finished ad drop to the person who uploads it — one verified link, or a refusal naming what is missing. Use whenever the owner says hand this off, send it to the email lead, the handoff, the handoff folder, give me the link for the ads, ship the drop, the ads are ready, the link for Ads Manager, or names a batch and a person. Ruled 2026-09-24: "there should be no question."
---

> **Activates component:** `components/ad-handoff` — `handoff.py` hands a finished piece to a role; `take_back.py` takes it back.

External dependencies: `components/ad-handoff/` (the gate), the drop at
`runs/image-teardown/<brand>/<drop>/deliverable/` on both planes (legacy
drops at `runs/image-edit/<brand>/<drop>/deliverable/`),
`components/naming/` (the convention the ad names are checked against).

**One command. It prints a link, or it refuses.**

```
python3 components/ad-handoff/handoff.py --brand <brand> --drop <drop> --for <email>
python3 components/ad-handoff/handoff.py --brand <brand> --drop <drop> --check    # verify only
```

`--for` is the person it is going to, by email; without it the access check
is skipped, which is how a handoff reaches someone who cannot open it.

## Never hand over a link this has not passed

the owner, 2026-09-24, after a handoff reached the email lead without the pictures:
*"stop these types of issues from happening … there should be no question.
You're wasting my time."* The seven checks are in
`components/ad-handoff/CLAUDE.md`, each with the day it bit. In short: every
ad has pictures, every ad has copy, the pictures are on **Drive** with bytes
(the local mount lies), every name parses, every funnel link answers 200,
the page carries its own Drive link, and the person can open the folder.

**A refusal is the answer.** Do not work around it, do not send the link
anyway, do not explain it away. Fix what it names, or tell the owner which of
the machines owes the fix — the pictures are `image-edit`'s, the copy is
`copywriter`'s, a dead link is the funnel's.

## What to send back

The link, and one line on what is in it. Nothing else — no paths, no
commands, no folder structure. If it refused, say what is missing and who
owes it, in one line each.

## When the drop does not exist yet

This gate hands over; it does not build. The drop is made by the image
chain and the draft standard (`image-draft`), varied by `image-variation`,
named by `naming`, and its copy comes from the copy machine. If there is no
`runs/image-teardown/<brand>/<drop>/deliverable/` (or a legacy one under
`runs/image-edit/`), that is the work to do first
— this is the last step, not the first.
