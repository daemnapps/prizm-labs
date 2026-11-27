---
name: email-design
description: Design the emails for a month — finished email copy goes in; each email's job card, section layout, pictures and a Klaviyo-ready build come out, in the brand's own look. Use whenever someone says "design the <brand> emails for <month>", "design email nov-02", "lay out the <brand> emails", "make the pictures for the <brand> emails", "redo the design for slot nov-02", "which design does this email get", "build the klaviyo version of nov-02", or hands over a run whose copy is finished and asks for the design.
---

# Email design

> **Activates component:** `components/email-production` — the `design/` line: `design/line.py` (job card and layout), `design/gaps.py` (prices and words), `design/build.py` (the Klaviyo build), `design/check.py` (the final check).

External dependencies: `components/email-production/design/` (the line), `components/email-production/prompts/` (design prompts, highest `-vN-` wins), `components/email-production/formats.json` and `components/marketing-calendar/definitions/email-kinds.json` (which email type gets which format), `brands/<brand>/email-sms/design-system.json` (the brand's look), `components/image-production/` (pictures that must be made).

Design starts only on **finished copy**. Writing the copy is the `email-production` skill. This skill is the second stage, and it is what `email-production` runs after the copy when you ask for a whole month.

## Say what is decided, then run it

Which design an email gets is decided by its **type** alone (occasion and avatar do not choose it). The calendar sets `kind` (design or letter) and `format` on each slot. Show the person that decision from `runs/marketing-calendar/<brand>/<YYYY-MM>/slots.json` before designing. A letter gets a plain letter layout; a design email gets a stack of sections.

```
python3 components/email-production/design/line.py <brand> <YYYY-MM> --only <slot ids> --dry-run
python3 components/email-production/design/line.py <brand> --run runs/email-production/<brand>/<label> [--pictures]
python3 components/email-production/design/gaps.py runs/email-production/<brand>/<label> --fill
python3 components/email-production/design/build.py runs/email-production/<brand>/<label>
python3 components/email-production/design/check.py runs/email-production/<brand>/<label> [more runs]
```

- `line.py` runs two model steps: the job card (design1) then the layout (design2). `--pictures` also makes every picture slot. Dry-run first and tell the person the email count.
- `gaps.py --fill` fills missing prices and words from the offer bank. `build.py` cuts the sections into pictures and live text for Klaviyo and writes the card. `check.py` runs the final check.
- Pictures: the real product first, then real proof or a brand photo we own, and only then a made picture from a real reference. Never a product or person from words alone.

## Rules

1. **Re-running design overwrites `design/email.json` and `design/job.json`.** A person's edits (the editor, the email lead, or the review step) live in `design/email.json`; a re-run destroys them, and a re-run of the copy followed by the design destroys them again. Before any re-run, check whether the person has edited it and ask. Never run it silently.
2. **`build.py` empties `klaviyo/assets/` on every rebuild.** It keeps the approval fields on `klaviyo/card.json`.
3. A section name the engine does not know is rejected. Sections are chosen by the model from the engine's list; the format is only a label it sees. A new section type needs engine code, not a data edit.
4. Brand facts come from `brands/<brand>/`, which this component never writes.
5. Nothing is sent, scheduled or uploaded from here. Upload is `email-upload`.

## What comes back, and where it lands

`runs/email-production/<brand>/<label>/design/` (`job.json`, `email.json`, `preview.html`, `promises.json`, `gaps.json`) and `runs/email-production/<brand>/<label>/klaviyo/` (`email.html`, `assets/`, `layout.json`, `card.json`).

Reply with the result and the folder it landed in (repo path or Drive folder name).
