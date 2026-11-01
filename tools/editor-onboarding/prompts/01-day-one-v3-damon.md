# Day one — v3

*Paste this into a new Higgsfield Supercomputer chat once, after Google Drive
and GitHub are connected (Connectors → Explore → connect both). In Claude
Code, paste it into a new session opened on the cloned repo. Replace
`{BRAND}` with the brand's name, `{ROLE}` with your role (video-editor,
graphic-designer, clipper or creator) and `{FOLDER LINK}` with the Google
Drive link to your own hand-off folder. Nothing else changes.*

*v3 (2026-10-01): work arrives in, and goes back through, your own hand-off
folder — `Shared Assets/handoffs/<role>/<brand>/<name>/` — not the brand
folder's `briefs/` queue. v2 (2026-09-22): no invitations — the folder is
opened by link. v1 (2026-09-22): first version.*

---

```prompt
I am a new {ROLE} starting on {BRAND}. Set me up, then show me what is waiting. Do these in order and report each one before moving on.

1. CONNECTIONS. Confirm Google Drive and GitHub are both connected in this chat. If either is not, stop and tell me exactly which one, in one line — nothing below works without both.

2. THE TOOLS. Clone https://github.com/daemnapps/prizm-labs (if it is already cloned, pull it so it is current). Then read tools/editor-onboarding/SOP.md in full. That file is the way we work; treat it as standing instructions for every session with me from now on.

3. MY FOLDER. Open this Google Drive folder directly: {FOLDER LINK} — that is my hand-off folder, `Shared Assets/handoffs/{ROLE}/{BRAND}/<my name>/`. Do not search for it by name. If the link does not open, tell me in one line; do not look for another folder with the same name.

4. WHAT IS WAITING. Read every `handoff.md` in my folder — live from Drive, never from memory. Show me each hand-off in one line: what it is, how many briefs, and whether its `returned/` folder is empty or already has work in it.

5. WHAT I DO NEXT. Tell me, in five lines or fewer, what happens each time I sit down to work: I paste the "Pull briefs" prompt from tools/editor-onboarding/prompts/, you sync the tools and read my folder, we pick a hand-off, review it, produce the asks, run the edit, and I put the finished work in `returned/`. The team takes it back from there.

Rules for you, always:
- Never invent a brief, a scene, a product detail or a claim. If it is not in the hand-off folder, say "not in the brief" and ask.
- Never write into the hand-off's `briefs/`, `assets/` or `references/`. Finished work goes in `returned/` only.
- When something in Drive or GitHub cannot be reached, say which door failed in one line. Do not work around it silently.

Finish with one line: "Set up for {BRAND} — N hand-offs waiting."
```
