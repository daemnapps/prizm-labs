---
name: teardown-email
description: Run the email teardown — an email (words and pictures) goes in; its element labels and its brand-free construct come out. Use whenever someone says "tear down this email for <brand>", "email teardown", "strip this email to its structure", "what format is this email", "tear down our last send", or hands over a sent-email file or an .html export and names a brand.
---

# Email teardown

> **Not a component:** runs lab code in `lab/the owner/email-teardown` — runs lab code.


External dependencies: `lab/the owner/email-teardown/` (the machine), `brands/<brand>/email-sms/simple.json` (the brand's furniture words, read at run time), `components/elements` (the library).

**One command.**

```
python3 lab/the owner/email-teardown/tools/run.py <email.md, .txt or .html> --brand <brand>
python3 lab/the owner/email-teardown/tools/run.py <email> --brand <brand> --dry-run
```

- The source is a sent-email `.md`/`.txt` file or an `.html` export.
- `--brand` is required: it names whose furniture words to read and where
  the run files. There is no default.
- **`--dry-run` spends nothing** — resolves and fills every prompt, shows the
  model per step and where it would file, makes no model call, leaves no file.
- After a hold: fix the prompt (a new `-vN-` file) or the source, then
  `--rerun-from tear1|tear2|tear3`.

## What it does

The free scan (furniture lines and damage the code can see) → the read (THE
MESSAGE, PAGE FURNITURE and SOURCE DEFECTS kept apart) → element labels
(format, template, framework) → the construct, built from the message only.

## The rules the command enforces — do not work around any of them

1. **The strip is done in code, not asked for.** The furniture section leaves
   the record before the labelling and construct steps; they see item
   numbers, never the words.
2. **Brand facts come from the brand.** Which words are furniture lives in the
   brand's own email file; no brand is named in code or prompts.
3. **Every label is a real library row** or an honest `none-fits` with a
   proposed row. An unknown id is refused with the real ids named.
4. **Three gates:** inputs (the email is on file and not empty, the brand is
   real, every step has a prompt) · elements after the labels · copy twice
   (the record arrived in its parts; the construct carries no furniture
   phrase, no name for the sender's frame, no merge tag as code, no UNFILLED
   note, and ends on its LEFT OUT line). A held run says why in `check.json`.
5. **It does not write an email.** That is email production.

## What comes back

`runs/email-teardown/<brand>/<label>/` — `tear1--record.md`,
`elements.json`, `tear3--construct.md`, every prompt as sent, `run.json`,
`check.json`.

Report: the format, template and framework it labelled, the construct in one
line, and whether it was held and why.

Reply with the result and the folder it landed in (repo path or Drive folder name).
