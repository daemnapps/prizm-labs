# Day one — v1

*Paste this into a new Higgsfield Supercomputer chat once, after Google Drive
and GitHub are connected (Connectors → Explore → connect both). Replace
`{BRAND}` with the brand folder's name. Nothing else changes.*

*v1 (2026-09-22): first version, written from the 21 Sep walkthrough.*

---

```prompt
I am a new editor/designer starting on {BRAND}. Set me up, then show me what is waiting. Do these in order and report each one before moving on.

1. CONNECTIONS. Confirm Google Drive and GitHub are both connected in this chat. If either is not, stop and tell me exactly which one, in one line — nothing below works without both.

2. THE TOOLS. Clone https://github.com/daemnapps/prizm-labs (if it is already cloned, pull it so it is current). Then read tools/21-editor-onboarding/SOP.md in full. That file is the way we work; treat it as standing instructions for every session with me from now on.

3. THE BRAND FOLDER. In Google Drive, find the folder for {BRAND} and inside it the folder named `briefs`. If you find more than one candidate, show me the paths and ask which — do not guess. If you cannot find it, tell me and I will paste the folder link.

4. THE QUEUE. Open `briefs/QUEUE.md` in that folder — read it live from Drive, never from memory. Show me the whole table as it stands: every brief, its type, status, who has it, the bounty and the due date.

5. WHAT I DO NEXT. Tell me, in five lines or fewer, what happens each time I sit down to work: I paste the "Pull briefs" prompt from tools/21-editor-onboarding/prompts/, you sync the tools and the queue, we pick a brief, review it, produce the asks, and I deliver into `briefs/delivered/`.

Rules for you, always:
- Never invent a brief, a scene, a product detail or a claim. If it is not in the brief package or the brand folder, say "not in the brief" and ask.
- Never write into a brief's source package. Deliveries go to `briefs/delivered/<brief>/` only.
- When something in Drive or GitHub cannot be reached, say which door failed in one line. Do not work around it silently.

Finish with one line: "Set up for {BRAND} — N briefs open."
```
