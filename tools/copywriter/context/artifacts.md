# Artifacts from the copy machine

One artifact per subject. Read this before creating a new one — if the subject
is already here, republish over that URL rather than opening a second page.

| Subject | Artifact | URL |
|---|---|---|
| Every finished body, headline and description this machine has written, by source, with a copy button on each | Copy Output | (team page) |
| The formats every source gets written to — length, form, opening, what each reads as | Copy Format Bank (SUPERSEDED by Copy Channel Map — retire candidate) | (team page) |
| First-principles map of every copy channel — reader state, formats, evidence held | Copy Channel Map | (team page) |
| Every piece of copy we hold, categorized by channel and format — 1,243 pieces, swiped and ours | Copy Library | (team page) |
| How to run this machine — what it needs, the exact commands, what comes out, and who clears each refusal | Running the Copy Machine | (team page) |

Markdown mirror of the runbook: `docs/running-the-copy-machine.md`.

**How the page is made.** `publish.py <label>` lifts a finished run out of
`results/` into `output/`; `build_copy_page.py` reads `output/` and writes
`copy-page.html`; that file is the artifact. Publishing the run is a separate
step from running it — a finished run that was never published shows up
nowhere, and nothing says so.
