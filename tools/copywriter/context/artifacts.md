# Artifacts from the copy machine

One artifact per subject. Read this before creating a new one — if the subject
is already here, republish over that URL rather than opening a second page.

| Subject | Artifact | URL |
|---|---|---|
| Every finished body, headline and description this machine has written, by source, with a copy button on each | Copy Output | https://claude.ai/code/artifact/2042474e-da9a-497f-afe5-9b4cec046678 |
| The formats every source gets written to — length, form, opening, what each reads as | Copy Format Bank (SUPERSEDED by Copy Channel Map — retire candidate) | https://claude.ai/code/artifact/f432d7f2-8397-4a9a-b4b1-8fe31a95aafe |
| First-principles map of every copy channel — reader state, formats, evidence held | Copy Channel Map | https://claude.ai/code/artifact/5493d4ce-f2c4-4398-a5c6-255d84a040d4 |
| Every piece of copy we hold, categorized by channel and format — 1,243 pieces, swiped and ours | Copy Library | https://claude.ai/code/artifact/b793833b-caa9-4625-a0d7-39ec2b53649b |

**How the page is made.** `publish.py <label>` lifts a finished run out of
`results/` into `output/`; `build_copy_page.py` reads `output/` and writes
`copy-page.html`; that file is the artifact. Publishing the run is a separate
step from running it — a finished run that was never published shows up
nowhere, and nothing says so.
